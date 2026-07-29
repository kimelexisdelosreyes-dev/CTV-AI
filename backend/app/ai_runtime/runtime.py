import asyncio

from .contracts import AdapterResult, AttemptStatus, ExecutionAttempt, RuntimeRequest, RuntimeResult, RuntimeStatus
from .registry import AIModelAdapterRegistry


class AIModelRuntime:
    def __init__(self, registry: AIModelAdapterRegistry) -> None:
        self._registry = registry

    async def execute(self, request: RuntimeRequest) -> RuntimeResult:
        execution_id, plan, cancelled = request.execution_id, request.plan, request.cancelled
        attempts: list[ExecutionAttempt] = []
        diagnostics: list[str] = []
        for fallback_index, model_id in enumerate((plan.model_id, *plan.fallback_model_ids)):
            retries = 0
            while retries <= plan.max_retries:
                if cancelled and cancelled.is_set():
                    return self._result(execution_id, plan, RuntimeStatus.CANCELLED, None, None, None, attempts, diagnostics + ["cancelled"])
                adapter = self._registry.resolve(model_id=model_id, provider_type=plan.provider_type, location=plan.location, mode=plan.mode)
                attempt_id = f"{execution_id}:attempt:{len(attempts) + 1}"
                if not adapter:
                    attempts.append(ExecutionAttempt(attempt_id, len(attempts) + 1, model_id, None, AttemptStatus.INCOMPATIBLE, retries, fallback_index))
                    diagnostics.append("adapter-unavailable")
                    break
                result = await self._run(adapter, execution_id, model_id, request.messages, cancelled, plan.timeout_ms)
                status = AttemptStatus.SUCCEEDED if result.status is RuntimeStatus.SUCCEEDED else AttemptStatus.TIMED_OUT if result.status is RuntimeStatus.TIMED_OUT else AttemptStatus.CANCELLED if result.status is RuntimeStatus.CANCELLED else AttemptStatus.FAILED
                attempts.append(ExecutionAttempt(attempt_id, len(attempts) + 1, model_id, adapter.descriptor.adapter_id, status, retries, fallback_index, result.error_code))
                if result.status is RuntimeStatus.SUCCEEDED:
                    return self._result(execution_id, plan, RuntimeStatus.SUCCEEDED, result.output, model_id, adapter.descriptor.adapter_id, attempts, diagnostics)
                if result.status is RuntimeStatus.CANCELLED:
                    return self._result(execution_id, plan, RuntimeStatus.CANCELLED, None, None, None, attempts, diagnostics + ["cancelled"])
                if result.retryable and retries < plan.max_retries:
                    retries += 1
                    continue
                if not result.fallback_eligible:
                    return self._result(execution_id, plan, result.status, None, None, None, attempts, diagnostics)
                break
        return self._result(execution_id, plan, RuntimeStatus.FAILED, None, None, None, attempts, diagnostics)

    async def _run(self, adapter, execution_id, model_id, messages, cancelled, timeout_ms) -> AdapterResult:
        task = asyncio.create_task(adapter.execute(execution_id=execution_id, model_id=model_id, messages=messages, cancelled=cancelled))
        cancellation = asyncio.create_task(cancelled.wait()) if cancelled else None
        try:
            wait_set = {task, *([cancellation] if cancellation else [])}
            done, _ = await asyncio.wait(wait_set, timeout=timeout_ms / 1000, return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                try:
                    return task.result()
                except asyncio.CancelledError:
                    return AdapterResult(RuntimeStatus.CANCELLED, adapter.descriptor.adapter_id, model_id, error_code="cancelled", error_category="cancellation")
                except Exception:
                    return AdapterResult(RuntimeStatus.FAILED, adapter.descriptor.adapter_id, model_id, error_code="adapter-execution", error_category="transport", retryable=True, fallback_eligible=True)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            if cancelled and cancelled.is_set():
                return AdapterResult(RuntimeStatus.CANCELLED, adapter.descriptor.adapter_id, model_id, error_code="cancelled", error_category="cancellation")
            return AdapterResult(RuntimeStatus.TIMED_OUT, adapter.descriptor.adapter_id, model_id, error_code="timeout", error_category="timeout", fallback_eligible=True)
        finally:
            if cancellation and not cancellation.done():
                cancellation.cancel()
            if not task.done():
                task.cancel()

    @staticmethod
    def _result(execution_id, plan, status, output, model, adapter, attempts, diagnostics):
        return RuntimeResult(execution_id, status, plan.plan_id, plan.fingerprint, output, model, adapter, tuple(attempts), tuple(diagnostics), (("attempt_count", len(attempts)), ("fallback_count", sum(item.fallback_index > 0 for item in attempts))), (("registry_version", plan.registry_version),))
