import asyncio
import time
import uuid
from types import SimpleNamespace

import pytest

from app.core.context_requirements import ContextRequirements
from app.schemas.context import ContextBundle, ContextMetadata
from app.schemas.knowledge import KnowledgeSource
from app.services import context_retrieval_coordinator as coordinator_module
from app.services.context_retrieval_coordinator import (
    ContextRetrievalCoordinator,
)
from app.services.intelligence_router import RouteDecision
from app.services.operations_context_service import OperationsContext
from app.services.performance_instrumentation import AskPerformanceInstrumentation
from app.services.service_errors import CompanyBrainServiceError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def requirements(**overrides) -> ContextRequirements:
    defaults = {
        "include_knowledge": True,
        "include_operations": True,
        "include_employee": False,
        "include_history": False,
        "knowledge_collections": ["company-policies"],
        "max_knowledge_chunks": 4,
        "max_knowledge_chars": 3200,
        "max_operational_tasks": 6,
        "max_operational_chars": 2200,
        "max_employee_context_chars": 900,
        "max_history_messages": 4,
        "max_history_chars": 1200,
        "max_total_prompt_chars": 5200,
    }
    defaults.update(overrides)
    return ContextRequirements(**defaults)


def route(intent: str = "mixed") -> RouteDecision:
    return RouteDecision(
        intent=intent,
        confidence=0.8,
        use_employee_context=intent == "employee",
        use_operations=True,
        collections=["company-policies"],
        sources=["knowledge", "operations"],
        context_requirements=requirements(),
    )


def source() -> KnowledgeSource:
    return KnowledgeSource(
        document_id="doc-1",
        filename="policy.pdf",
        category="company-policies",
        chunk_index=1,
        page_number=1,
        text="Approved policy text.",
        score=0.95,
    )


def operations() -> OperationsContext:
    return OperationsContext(
        applied=True,
        text="[Monday Task 1] Important work | ID: 1",
        task_count=1,
        board_count=1,
        summary="1 active.",
        original_task_count=1,
        original_chars=35,
        final_chars=35,
    )


@pytest.mark.anyio
async def test_knowledge_and_operations_execute_concurrently(monkeypatch) -> None:
    async def fetch_knowledge(*_):
        await asyncio.sleep(0.2)
        return [source()]

    async def fetch_operations(*_, **__):
        await asyncio.sleep(0.3)
        return operations()

    monkeypatch.setattr(
        coordinator_module.operations_context_service,
        "build",
        fetch_operations,
    )

    coordinator = ContextRetrievalCoordinator()
    instrumentation = AskPerformanceInstrumentation()
    started = time.perf_counter()
    result = await coordinator.retrieve(
        question="Combine current operations priorities with approved guidance.",
        top_k=5,
        routed_collections=["company-policies"],
        requirements=requirements(),
        route=route(),
        current_user=SimpleNamespace(),
        db=SimpleNamespace(),
        conversation_id=None,
        knowledge_fetcher=fetch_knowledge,
        instrumentation=instrumentation,
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.45
    assert result.parallel_execution_used is True
    assert result.knowledge == [source()]
    assert result.operations is not None
    assert result.component_statuses == {
        "knowledge": "success",
        "operations": "success",
    }
    assert instrumentation.metrics["retrieval_parallel_used"] is True
    assert instrumentation.metrics["retrieval_total_duration_ms"] < 450
    assert instrumentation.metrics["knowledge_retrieval_duration_ms"] >= 190
    assert instrumentation.metrics["operations_retrieval_duration_ms"] >= 290
    assert instrumentation.metrics["parallel_time_saved_estimate_ms"] > 100


@pytest.mark.anyio
async def test_employee_and_history_share_db_session_sequentially(monkeypatch) -> None:
    calls: list[str] = []

    async def fetch_employee(*_, **__):
        calls.append("employee:start")
        await asyncio.sleep(0.02)
        calls.append("employee:end")
        return ContextBundle(
            system_context="EMPLOYEE CONTEXT",
            metadata=ContextMetadata(applied=True),
        )

    async def fetch_history(*_, **__):
        calls.append("history:start")
        await asyncio.sleep(0.02)
        calls.append("history:end")
        return [
            SimpleNamespace(
                role=SimpleNamespace(value="assistant"),
                content="Previous safe summary.",
            )
        ]

    monkeypatch.setattr(
        coordinator_module.context_engine,
        "build_employee_context",
        fetch_employee,
    )
    monkeypatch.setattr(
        coordinator_module.conversation_service,
        "recent_messages",
        fetch_history,
    )

    result = await ContextRetrievalCoordinator().retrieve(
        question="Based on my role and preferences, what should I focus on next?",
        top_k=5,
        routed_collections=[],
        requirements=requirements(
            include_knowledge=False,
            include_operations=False,
            include_employee=True,
            include_history=True,
            knowledge_collections=[],
        ),
        route=route("employee"),
        current_user=SimpleNamespace(),
        db=SimpleNamespace(),
        conversation_id=uuid.uuid4(),
        knowledge_fetcher=lambda *_: asyncio.sleep(0),
    )

    assert calls == [
        "employee:start",
        "employee:end",
        "history:start",
        "history:end",
    ]
    assert result.parallel_execution_used is False
    assert result.employee is not None
    assert result.history == "Assistant: Previous safe summary."


@pytest.mark.anyio
async def test_unused_components_are_not_called(monkeypatch) -> None:
    async def fetch_knowledge(*_):
        raise AssertionError("knowledge should not be called")

    async def fetch_employee(*_, **__):
        raise AssertionError("employee should not be called")

    async def fetch_operations(*_, **__):
        return operations()

    monkeypatch.setattr(
        coordinator_module.context_engine,
        "build_employee_context",
        fetch_employee,
    )
    monkeypatch.setattr(
        coordinator_module.operations_context_service,
        "build",
        fetch_operations,
    )

    result = await ContextRetrievalCoordinator().retrieve(
        question="Which tasks are overdue?",
        top_k=5,
        routed_collections=[],
        requirements=requirements(
            include_knowledge=False,
            include_operations=True,
            knowledge_collections=[],
        ),
        route=route("operations"),
        current_user=SimpleNamespace(),
        db=SimpleNamespace(),
        conversation_id=None,
        knowledge_fetcher=fetch_knowledge,
    )

    assert result.operations is not None
    assert result.component_statuses == {"operations": "success"}


@pytest.mark.anyio
async def test_required_component_failure_is_controlled() -> None:
    async def fetch_knowledge(*_):
        raise CompanyBrainServiceError(
            category="embedding_model_missing",
            status_code=503,
            safe_detail="The configured embedding model is not available.",
        )

    with pytest.raises(CompanyBrainServiceError) as exc:
        await ContextRetrievalCoordinator().retrieve(
            question="What company policy applies?",
            top_k=5,
            routed_collections=["company-policies"],
            requirements=requirements(include_operations=False),
            route=route("policy"),
            current_user=SimpleNamespace(),
            db=SimpleNamespace(),
            conversation_id=None,
            knowledge_fetcher=fetch_knowledge,
            instrumentation=AskPerformanceInstrumentation(),
        )

    assert exc.value.category == "embedding_model_missing"
    assert exc.value.safe_detail == "The configured embedding model is not available."


@pytest.mark.anyio
async def test_optional_component_failure_degrades(monkeypatch) -> None:
    async def fetch_employee(*_, **__):
        raise RuntimeError("sensitive employee detail")

    async def fetch_operations(*_, **__):
        return operations()

    monkeypatch.setattr(
        coordinator_module.context_engine,
        "build_employee_context",
        fetch_employee,
    )
    monkeypatch.setattr(
        coordinator_module.operations_context_service,
        "build",
        fetch_operations,
    )

    result = await ContextRetrievalCoordinator().retrieve(
        question="What are my operations priorities?",
        top_k=5,
        routed_collections=[],
        requirements=requirements(
            include_knowledge=False,
            include_operations=True,
            include_employee=True,
            knowledge_collections=[],
        ),
        route=route("operations"),
        current_user=SimpleNamespace(),
        db=SimpleNamespace(),
        conversation_id=None,
        knowledge_fetcher=lambda *_: asyncio.sleep(0),
    )

    assert result.context_degraded is True
    assert result.unavailable_context_components == ["employee"]
    assert result.required_context_failure is None
    assert result.operations is not None


@pytest.mark.anyio
async def test_component_timeout_is_classified_and_cancels_task(monkeypatch) -> None:
    cancelled = False

    async def fetch_knowledge(*_):
        nonlocal cancelled
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled = True
            raise
        return [source()]

    monkeypatch.setattr(
        coordinator_module.settings,
        "company_brain_knowledge_timeout_seconds",
        0.01,
    )

    with pytest.raises(CompanyBrainServiceError) as exc:
        await ContextRetrievalCoordinator().retrieve(
            question="What company policy applies?",
            top_k=5,
            routed_collections=["company-policies"],
            requirements=requirements(include_operations=False),
            route=route("policy"),
            current_user=SimpleNamespace(),
            db=SimpleNamespace(),
            conversation_id=None,
            knowledge_fetcher=fetch_knowledge,
        )

    assert exc.value.category == "context_knowledge_timeout"
    assert cancelled is True


@pytest.mark.anyio
async def test_no_duplicate_retrieval_calls(monkeypatch) -> None:
    calls = {"knowledge": 0, "operations": 0}

    async def fetch_knowledge(*_):
        calls["knowledge"] += 1
        return [source()]

    async def fetch_operations(*_, **__):
        calls["operations"] += 1
        return operations()

    monkeypatch.setattr(
        coordinator_module.operations_context_service,
        "build",
        fetch_operations,
    )

    await ContextRetrievalCoordinator().retrieve(
        question="Combine current operations priorities with approved guidance.",
        top_k=5,
        routed_collections=["company-policies"],
        requirements=requirements(),
        route=route(),
        current_user=SimpleNamespace(),
        db=SimpleNamespace(),
        conversation_id=None,
        knowledge_fetcher=fetch_knowledge,
    )

    assert calls == {"knowledge": 1, "operations": 1}
