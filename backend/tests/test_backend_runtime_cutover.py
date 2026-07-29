import asyncio

import pytest
from pydantic import ValidationError

from app.ai_runtime import RuntimeStatus
from app.core.config import Settings, settings
from app.services.ai_router import AIRouter


class Shadow:
    async def route_messages(self, *, messages, **kwargs):
        self.messages = messages
        return messages, None, None


class Service:
    def __init__(self): self.calls = []
    async def chat(self, messages, model=None, return_metadata=False):
        self.calls.append((messages, model, return_metadata))
        return ("runtime answer", {"prompt_eval_count": 2, "eval_count": 3}) if return_metadata else "legacy answer"


@pytest.mark.asyncio
async def test_flag_absent_or_false_uses_exact_legacy_service_call():
    service, shadow = Service(), Shadow()
    router = AIRouter(ollama=service, runtime_enabled=False, shadow_service=shadow)
    assert await router.chat("hello", "general") == "legacy answer"
    assert len(service.calls) == 1 and service.calls[0][1:] == (None, False)
    assert service.calls[0][0] == shadow.messages
    assert router._runtime is None


@pytest.mark.asyncio
async def test_runtime_flag_preserves_messages_model_and_response_shape(monkeypatch):
    monkeypatch.setattr(settings, "ollama_model", "qwen3:8b")
    service, shadow = Service(), Shadow()
    router = AIRouter(ollama=service, runtime_enabled=True, shadow_service=shadow)
    assert await router.chat("hello  ", "general") == "runtime answer"
    assert len(service.calls) == 1
    messages, model, metadata = service.calls[0]
    assert messages == shadow.messages and model == "qwen3:8b" and metadata is True
    assert messages[0]["role"] == "system" and messages[1] == {"role": "user", "content": "hello  "}


@pytest.mark.asyncio
async def test_runtime_failure_does_not_execute_legacy():
    class FailedRuntime:
        async def execute(self, request):
            return type("Result", (), {"status": RuntimeStatus.FAILED, "attempts": (), "execution_id": "x", "plan_id": "x", "completed_adapter_id": None, "statistics": (), "diagnostics": ()})()
    service = Service()
    router = AIRouter(ollama=service, runtime=FailedRuntime(), runtime_enabled=True, shadow_service=Shadow())
    with pytest.raises(Exception):
        await router.chat("hello", "general")
    assert service.calls == []


@pytest.mark.asyncio
async def test_separate_runtime_requests_do_not_share_messages():
    service = Service(); router = AIRouter(ollama=service, runtime_enabled=True, shadow_service=Shadow())
    await asyncio.gather(router.chat("one", "general"), router.chat("two", "general"))
    assert {call[0][1]["content"] for call in service.calls} == {"one", "two"}


def test_runtime_flag_invalid_value_uses_settings_validation():
    with pytest.raises(ValidationError):
        Settings(ctv_one_ai_runtime_enabled="not-a-boolean")
