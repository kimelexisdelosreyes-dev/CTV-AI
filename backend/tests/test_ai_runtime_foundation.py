import asyncio
import json
from dataclasses import FrozenInstanceError

import pytest

from app.ai_runtime import AIModelAdapterRegistry, AIModelRuntime, ExecutionPlan, MessageRole, RuntimeMessage, RuntimeRequest, RuntimeStatus
from app.ai_runtime.test_adapter import DeterministicTestAdapter


def plan(): return ExecutionPlan("plan-1", "fp-1", "context-1", "registry-1", "test-model", "internal")
def messages(): return (RuntimeMessage(MessageRole.SYSTEM, "Rules"), RuntimeMessage("user", "Question"), RuntimeMessage("assistant", "Answer"), RuntimeMessage("user", "Follow-up"), RuntimeMessage("assistant", "Final answer"))
def request(event=None): return RuntimeRequest("run-1", plan(), messages(), event)


def test_message_contract_is_immutable_validated_ordered_and_serializable():
    conversation = messages()
    assert [message.role.value for message in conversation] == ["system", "user", "assistant", "user", "assistant"]
    assert json.dumps(RuntimeRequest("run-1", plan(), conversation).to_dict())
    with pytest.raises(FrozenInstanceError): conversation[0].content = "changed"
    with pytest.raises(TypeError): RuntimeRequest("run-1", plan(), list(conversation))
    with pytest.raises(ValueError): RuntimeMessage("tool", "not supported")


def test_runtime_succeeds_and_result_is_immutable_and_does_not_retain_messages():
    registry = AIModelAdapterRegistry(); registry.register(DeterministicTestAdapter())
    result = asyncio.run(AIModelRuntime(registry).execute(request()))
    assert result.status is RuntimeStatus.SUCCEEDED and result.output == "deterministic-test-output"
    assert "Question" not in json.dumps(result.to_dict())
    with pytest.raises(FrozenInstanceError): result.status = RuntimeStatus.FAILED


def test_runtime_pre_execution_cancellation_is_terminal():
    registry = AIModelAdapterRegistry(); registry.register(DeterministicTestAdapter())
    event = asyncio.Event(); event.set()
    assert asyncio.run(AIModelRuntime(registry).execute(request(event))).status is RuntimeStatus.CANCELLED


def test_runtime_cooperative_cancellation_cancels_active_adapter():
    class WaitingAdapter(DeterministicTestAdapter):
        cancelled_in_flight = False
        async def execute(self, **kwargs):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled_in_flight = True
                raise
    async def run():
        registry = AIModelAdapterRegistry(); adapter = WaitingAdapter(); registry.register(adapter)
        event = asyncio.Event(); task = asyncio.create_task(AIModelRuntime(registry).execute(request(event)))
        await asyncio.sleep(0); event.set()
        return await task, adapter
    result, adapter = asyncio.run(run())
    assert result.status is RuntimeStatus.CANCELLED and adapter.cancelled_in_flight
