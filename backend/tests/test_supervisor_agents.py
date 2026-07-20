import asyncio
from types import SimpleNamespace

import pytest

from app.supervisor import agents as agent_module
from app.supervisor.agents import AgentExecutionContext, invoke_agent_model


@pytest.mark.asyncio
async def test_inference_agent_uses_queue_and_releases_lease_on_cancellation(
    monkeypatch,
) -> None:
    chat_started = asyncio.Event()
    released = []
    submissions = []

    class Lease:
        async def release(self, *, cancelled=False):
            released.append(cancelled)

    class Admission:
        initial_result = SimpleNamespace()

        async def wait(self):
            return Lease()

    class Queue:
        async def submit(self, **kwargs):
            submissions.append(kwargs)
            return Admission()

        @staticmethod
        def record_result(*_):
            return None

        @staticmethod
        def record_lease(*_):
            return None

    async def blocking_chat(*_, **__):
        chat_started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(agent_module, "inference_queue", Queue())
    monkeypatch.setattr(agent_module.ollama_service, "chat", blocking_chat)
    context = AgentExecutionContext(
        user=SimpleNamespace(id="user-1"),
        db=None,
        question="question",
        top_k=5,
        route=None,
        requirements=None,
        instrumentation=SimpleNamespace(
            request_id="request-1",
            model_name=None,
            record_metric=lambda *_: None,
        ),
        knowledge_fetcher=None,
    )
    running = asyncio.create_task(
        invoke_agent_model(
            messages=[{"role": "user", "content": "safe"}],
            model_name="test-model",
            model_role="reasoning",
            context=context,
        )
    )
    await asyncio.wait_for(chat_started.wait(), timeout=1)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running

    assert submissions[0]["model_name"] == "test-model"
    assert submissions[0]["request_id"] == "request-1"
    assert released == [True]
