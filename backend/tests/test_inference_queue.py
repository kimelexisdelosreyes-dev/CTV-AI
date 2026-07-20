import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.services.inference_queue import (
    InferenceQueueConfig,
    InferenceQueueError,
    InferenceQueueService,
    normalize_model_env_key,
    priority_for_model_role,
)
from app.schemas.context import ContextMetadata
from app.schemas.knowledge import KnowledgeSource
from app.core.config import settings
from app.services import knowledge_service
from app.services.knowledge_service import answer_with_knowledge
from app.services.performance_instrumentation import AskPerformanceInstrumentation
from app.services.semantic_cache import SemanticCacheResult


def queue_config(**overrides) -> InferenceQueueConfig:
    values = {
        "enabled": True,
        "global_concurrency": 2,
        "queue_capacity": 20,
        "default_timeout_seconds": 1.0,
        "queue_wait_timeout_seconds": 1.0,
        "per_user_active_limit": 1,
        "per_user_queue_limit": 3,
        "shutdown_grace_seconds": 0.01,
        "aging_seconds": 10.0,
        "model_limits": {"qwen3:8b": 2, "deepseek-r1:14b": 1},
    }
    values.update(overrides)
    return InferenceQueueConfig(**values)


async def lease_for(service: InferenceQueueService, **kwargs):
    admission = await service.submit(**kwargs)
    return await admission.wait()


def request_args(user: str, model: str = "qwen3:8b", role: str = "fast"):
    return {"user_id": user, "model_name": model, "model_role": role}


def test_model_key_normalization_and_priority_are_deterministic() -> None:
    assert normalize_model_env_key("deepseek-r1:14b") == "DEEPSEEK_R1_14B"
    assert priority_for_model_role("reasoning") == "interactive_reasoning"
    assert priority_for_model_role("operations") == "interactive_fast"
    assert priority_for_model_role("balanced") == "interactive_standard"


@pytest.mark.asyncio
async def test_semantic_cache_hit_bypasses_queue_and_ollama(monkeypatch) -> None:
    async def build_lookup(**_):
        return None

    async def lookup(_):
        return SemanticCacheResult(
            hit=True,
            hit_type="exact",
            answer="Cached answer",
            personalization=ContextMetadata(),
            selected_model="qwen3:8b",
        )

    async def forbidden_chat(*_, **__):
        raise AssertionError("Ollama must not run on a cache hit")

    monkeypatch.setattr(knowledge_service.semantic_cache, "build_lookup", build_lookup)
    monkeypatch.setattr(knowledge_service.semantic_cache, "lookup", lookup)
    monkeypatch.setattr(knowledge_service.ollama_service, "chat", forbidden_chat)
    instrumentation = AskPerformanceInstrumentation()
    answer, sources, _ = await answer_with_knowledge(
        question="What is our leave policy?",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=False,
        current_user=SimpleNamespace(id=uuid.uuid4()),
        db=None,
        instrumentation=instrumentation,
    )
    assert answer == "Cached answer"
    assert sources == []
    assert instrumentation.metrics["ollama_skipped_due_to_cache"] is True
    assert instrumentation.metrics["inference_queue_bypassed"] is True
    assert instrumentation.metrics["inference_queue_admitted"] is False


def configure_cache_miss_pipeline(monkeypatch, service, chat) -> None:
    async def build_lookup(**_):
        return None

    async def lookup(_):
        return SemanticCacheResult(skip_reason="test_miss")

    async def search(*_args, **_kwargs):
        return [
            KnowledgeSource(
                document_id="doc-1",
                filename="policy.pdf",
                category="company-policies",
                chunk_index=0,
                page_number=1,
                text="Approved leave policy.",
                score=0.99,
            )
        ]

    monkeypatch.setattr(knowledge_service.semantic_cache, "build_lookup", build_lookup)
    monkeypatch.setattr(knowledge_service.semantic_cache, "lookup", lookup)
    monkeypatch.setattr(knowledge_service, "_search_routed_collections", search)
    monkeypatch.setattr(knowledge_service, "inference_queue", service)
    monkeypatch.setattr(knowledge_service.ollama_service, "chat", chat)
    monkeypatch.setattr(settings, "ctv_one_model_router_enabled", False)


@pytest.mark.asyncio
async def test_inference_timeout_releases_global_and_model_slots(monkeypatch) -> None:
    service = InferenceQueueService(
        queue_config(global_concurrency=1, default_timeout_seconds=0.01)
    )

    async def slow_chat(*_args, **_kwargs):
        await asyncio.sleep(0.1)

    configure_cache_miss_pipeline(monkeypatch, service, slow_chat)
    with pytest.raises(knowledge_service.OllamaInferenceTimeoutError):
        await answer_with_knowledge(
            question="What company policy applies to leave requests?",
            top_k=5,
            category=None,
            assistant="general",
            use_employee_context=False,
            current_user=SimpleNamespace(id=uuid.uuid4()),
            db=None,
            instrumentation=AskPerformanceInstrumentation(),
        )
    status = await service.status()
    assert status["active_global"] == 0
    assert status["active_by_model"][settings.ollama_model] == 0


@pytest.mark.asyncio
async def test_cancellation_during_inference_releases_lease(monkeypatch) -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    inference_started = asyncio.Event()

    async def waiting_chat(*_args, **_kwargs):
        inference_started.set()
        await asyncio.Event().wait()

    configure_cache_miss_pipeline(monkeypatch, service, waiting_chat)
    task = asyncio.create_task(
        answer_with_knowledge(
            question="What company policy applies to leave requests?",
            top_k=5,
            category=None,
            assistant="general",
            use_employee_context=False,
            current_user=SimpleNamespace(id=uuid.uuid4()),
            db=None,
            instrumentation=AskPerformanceInstrumentation(),
        )
    )
    await asyncio.wait_for(inference_started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    status = await service.status()
    assert status["active_global"] == 0
    assert status["recent_cancellations"] == 1


@pytest.mark.asyncio
async def test_disabled_queue_preserves_immediate_behavior() -> None:
    service = InferenceQueueService(queue_config(enabled=False))
    admission = await service.submit(**request_args("u1"))
    lease = await admission.wait()
    assert admission.initial_result.admitted is True
    assert admission.initial_result.queued is False
    assert (await service.status())["active_global"] == 0
    await lease.release()


@pytest.mark.asyncio
async def test_global_concurrency_is_enforced() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    first = await lease_for(service, **request_args("u1"))
    second_admission = await service.submit(**request_args("u2"))
    assert second_admission.initial_result.queued is True
    assert (await service.status())["active_global"] == 1
    await first.release()
    second = await second_admission.wait()
    assert second.active_global == 1
    await second.release()


@pytest.mark.asyncio
async def test_model_limit_allows_other_model_to_proceed() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=2))
    reasoning = await lease_for(
        service,
        **request_args("u1", "deepseek-r1:14b", "reasoning"),
    )
    queued_reasoning = await service.submit(
        **request_args("u2", "deepseek-r1:14b", "reasoning")
    )
    fast = await lease_for(service, **request_args("u3"))
    assert queued_reasoning.initial_result.queued is True
    assert fast.active_global == 2
    await fast.release()
    assert not queued_reasoning.pending.future.done()
    await reasoning.release()
    second_reasoning = await queued_reasoning.wait()
    await second_reasoning.release()


@pytest.mark.asyncio
async def test_per_user_active_limit_preserves_slot_for_another_user() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=2))
    first = await lease_for(service, **request_args("u1"))
    same_user = await service.submit(**request_args("u1"))
    other_user = await lease_for(service, **request_args("u2"))
    assert same_user.initial_result.queued is True
    assert other_user.active_global == 2
    await first.release()
    replacement = await same_user.wait()
    await other_user.release()
    await replacement.release()


@pytest.mark.asyncio
async def test_per_user_queue_limit_rejects_safely() -> None:
    service = InferenceQueueService(queue_config(per_user_queue_limit=1))
    active = await lease_for(service, **request_args("u1"))
    waiting = await service.submit(**request_args("u1"))
    rejected = await service.submit(**request_args("u1"))
    with pytest.raises(InferenceQueueError) as caught:
        await rejected.wait()
    assert caught.value.category == "per_user_queue_limit"
    assert caught.value.status_code == 429
    await waiting.cancel()
    await active.release()


@pytest.mark.asyncio
async def test_global_queue_capacity_returns_controlled_overload() -> None:
    service = InferenceQueueService(
        queue_config(global_concurrency=1, queue_capacity=1)
    )
    active = await lease_for(service, **request_args("blocker"))
    waiting = await service.submit(**request_args("u1"))
    rejected = await service.submit(**request_args("u2"))
    with pytest.raises(InferenceQueueError) as caught:
        await rejected.wait()
    assert caught.value.category == "queue_full"
    assert caught.value.retry_after_seconds >= 1
    await waiting.cancel()
    await active.release()


@pytest.mark.asyncio
async def test_fifo_is_preserved_within_user_and_priority() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    blocker = await lease_for(service, **request_args("blocker"))
    first = await service.submit(request_id="first", **request_args("u1"))
    second = await service.submit(request_id="second", **request_args("u1"))
    await blocker.release()
    first_lease = await first.wait()
    assert first_lease.request_id == "first"
    await first_lease.release()
    second_lease = await second.wait()
    assert second_lease.request_id == "second"
    await second_lease.release()


@pytest.mark.asyncio
async def test_interactive_work_precedes_background_work() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    blocker = await lease_for(service, **request_args("blocker"))
    background = await service.submit(
        priority="background",
        **request_args("background"),
    )
    interactive = await service.submit(
        priority="interactive_fast",
        **request_args("interactive"),
    )
    await blocker.release()
    interactive_lease = await interactive.wait()
    assert interactive_lease.request_id != background.pending.request.request_id
    await interactive_lease.release()
    background_lease = await background.wait()
    await background_lease.release()


@pytest.mark.asyncio
async def test_aging_prevents_background_starvation() -> None:
    service = InferenceQueueService(
        queue_config(global_concurrency=1, aging_seconds=0.01)
    )
    blocker = await lease_for(service, **request_args("blocker"))
    background = await service.submit(
        request_id="aged-background",
        priority="background",
        **request_args("background"),
    )
    await asyncio.sleep(0.035)
    interactive = await service.submit(
        request_id="new-interactive",
        priority="interactive_fast",
        **request_args("interactive"),
    )
    await blocker.release()
    aged_lease = await background.wait()
    assert aged_lease.request_id == "aged-background"
    assert not interactive.pending.future.done()
    await aged_lease.release()
    interactive_lease = await interactive.wait()
    await interactive_lease.release()


@pytest.mark.asyncio
async def test_round_robin_fairness_across_users() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    blocker = await lease_for(service, **request_args("blocker"))
    u1_first = await service.submit(request_id="u1-first", **request_args("u1"))
    u1_second = await service.submit(request_id="u1-second", **request_args("u1"))
    u2_first = await service.submit(request_id="u2-first", **request_args("u2"))
    await blocker.release()
    first = await u1_first.wait()
    await first.release()
    second = await u2_first.wait()
    assert second.request_id == "u2-first"
    assert not u1_second.pending.future.done()
    await second.release()
    third = await u1_second.wait()
    await third.release()


@pytest.mark.asyncio
async def test_queue_timeout_removes_entry_and_releases_capacity() -> None:
    service = InferenceQueueService(
        queue_config(global_concurrency=1, queue_wait_timeout_seconds=0.02)
    )
    active = await lease_for(service, **request_args("u1"))
    timed_out = await service.submit(**request_args("u2"))
    with pytest.raises(InferenceQueueError) as caught:
        await timed_out.wait(poll_seconds=0.005)
    assert caught.value.category == "queue_wait_timeout"
    assert (await service.status())["queued_total"] == 0
    await active.release()


@pytest.mark.asyncio
async def test_streaming_disconnect_removes_queued_request() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    active = await lease_for(service, **request_args("u1"))
    waiting = await service.submit(streaming=True, **request_args("u2"))

    async def disconnected() -> bool:
        return True

    with pytest.raises(asyncio.CancelledError):
        await waiting.wait(cancellation_check=disconnected)
    assert (await service.status())["queued_total"] == 0
    await active.release()


@pytest.mark.asyncio
async def test_task_cancellation_removes_queued_request() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    active = await lease_for(service, **request_args("u1"))
    waiting = await service.submit(**request_args("u2"))
    waiter = asyncio.create_task(waiting.wait())
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    assert (await service.status())["queued_total"] == 0
    await active.release()


@pytest.mark.asyncio
async def test_exception_and_cancellation_release_lease() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    lease = await lease_for(service, **request_args("u1"))
    with pytest.raises(RuntimeError):
        async with lease:
            raise RuntimeError("safe test failure")
    assert (await service.status())["active_global"] == 0

    cancelled = await lease_for(service, **request_args("u2"))
    await cancelled.release(cancelled=True)
    status = await service.status()
    assert status["active_global"] == 0
    assert status["recent_cancellations"] == 1


@pytest.mark.asyncio
async def test_shutdown_rejects_new_and_cancels_queued_requests() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    active = await lease_for(service, **request_args("u1"))
    queued = await service.submit(**request_args("u2"))
    await service.shutdown(grace_seconds=0)
    with pytest.raises(InferenceQueueError) as queued_error:
        await queued.wait()
    assert queued_error.value.category == "service_shutting_down"
    rejected = await service.submit(**request_args("u3"))
    with pytest.raises(InferenceQueueError) as new_error:
        await rejected.wait()
    assert new_error.value.category == "service_shutting_down"
    await active.release()


@pytest.mark.asyncio
async def test_diagnostics_are_aggregate_and_contain_no_sensitive_text() -> None:
    service = InferenceQueueService(queue_config(global_concurrency=1))
    lease = await lease_for(
        service,
        user_id="private-user-id",
        model_name="qwen3:8b",
        model_role="fast",
        conversation_id="private-conversation-id",
    )
    status = await service.status()
    serialized = str(status)
    assert "private-user-id" not in serialized
    assert "private-conversation-id" not in serialized
    assert set(status) == {
        "queue_enabled",
        "accepting_requests",
        "active_global",
        "global_limit",
        "queued_total",
        "queue_capacity",
        "active_by_model",
        "limits_by_model",
        "queued_by_priority",
        "active_by_priority",
        "oldest_wait_seconds",
        "average_wait_ms",
        "recent_rejections",
        "recent_timeouts",
        "recent_cancellations",
        "completed_count",
        "cache_bypass_count",
    }
    await lease.release()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("users", "requests_per_user", "expected_rejections"),
    [(10, 1, 0), (20, 2, 18)],
)
async def test_synthetic_multi_user_load_is_bounded(
    users: int,
    requests_per_user: int,
    expected_rejections: int,
) -> None:
    service = InferenceQueueService(
        queue_config(
            global_concurrency=2,
            queue_capacity=20,
            per_user_queue_limit=3,
        )
    )
    release_active = asyncio.Event()
    outcomes: list[str] = []

    async def request(user_index: int) -> None:
        admission = await service.submit(**request_args(f"u{user_index}"))
        try:
            lease = await admission.wait()
        except InferenceQueueError:
            outcomes.append("rejected")
            return
        outcomes.append("admitted")
        await release_active.wait()
        await lease.release()

    tasks = [
        asyncio.create_task(request(user_index))
        for user_index in range(users)
        for _ in range(requests_per_user)
    ]
    await asyncio.sleep(0.02)
    saturated = await service.status()
    assert saturated["active_global"] == 2
    assert saturated["queued_total"] <= 20
    release_active.set()
    await asyncio.gather(*tasks)
    assert outcomes.count("rejected") == expected_rejections
    assert (await service.status())["active_global"] == 0
    assert (await service.status())["queued_total"] == 0
