import asyncio,json
from dataclasses import FrozenInstanceError
import pytest
from app.ai_runtime import AIModelAdapterRegistry, AIModelRuntime, ExecutionPlan, RuntimeStatus
from app.ai_runtime.test_adapter import DeterministicTestAdapter
def plan():return ExecutionPlan("plan-1","fp-1","context-1","registry-1","test-model","internal")
def test_registry_is_deterministic_and_duplicate_safe():
 r=AIModelAdapterRegistry();r.register(DeterministicTestAdapter());assert r.snapshot()[0].adapter_id=="deterministic-test"
 with pytest.raises(ValueError):r.register(DeterministicTestAdapter())
def test_runtime_succeeds_and_result_is_immutable_and_serializable():
 r=AIModelAdapterRegistry();r.register(DeterministicTestAdapter());result=asyncio.run(AIModelRuntime(r).execute(execution_id="run-1",plan=plan(),content="not retained"));assert result.status is RuntimeStatus.SUCCEEDED and result.output=="deterministic-test-output";assert "not retained" not in json.dumps(result.__dict__)
 with pytest.raises(FrozenInstanceError):result.status=RuntimeStatus.FAILED
def test_runtime_cancellation_is_terminal():
 r=AIModelAdapterRegistry();r.register(DeterministicTestAdapter());event=asyncio.Event();event.set();result=asyncio.run(AIModelRuntime(r).execute(execution_id="run-1",plan=plan(),content="x",cancelled=event));assert result.status is RuntimeStatus.CANCELLED
