from types import SimpleNamespace

import pytest

from app.schemas.context import ContextBundle, ContextMetadata
from app.schemas.knowledge import KnowledgeSource
from app.services import knowledge_service
from app.services.knowledge_service import answer_with_knowledge
from app.services.operations_context_service import OperationsContext
from app.services.performance_instrumentation import AskPerformanceInstrumentation


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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


async def fake_chat(messages, model=None, return_metadata=False):
    fake_chat.messages = messages
    payload = {
        "prompt_eval_count": 10,
        "eval_count": 5,
        "eval_duration": 1_000_000_000,
    }
    if return_metadata:
        return "Generated answer.", payload
    return "Generated answer."


@pytest.mark.anyio
async def test_knowledge_only_route_excludes_employee_and_operations(monkeypatch) -> None:
    async def fake_search(*_):
        return [source()]

    async def fail_employee(*_, **__):
        raise AssertionError("employee context should not be built")

    async def fail_operations(*_, **__):
        raise AssertionError("operations context should not be built")

    monkeypatch.setattr(knowledge_service, "_search_routed_collections", fake_search)
    monkeypatch.setattr(
        knowledge_service.context_engine,
        "build_employee_context",
        fail_employee,
    )
    monkeypatch.setattr(
        knowledge_service.operations_context_service,
        "build",
        fail_operations,
    )
    monkeypatch.setattr(knowledge_service.ollama_service, "chat", fake_chat)

    instrumentation = AskPerformanceInstrumentation()
    answer, sources, personalization = await answer_with_knowledge(
        question="What company policy applies to leave requests?",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=True,
        current_user=SimpleNamespace(),
        db=None,
        instrumentation=instrumentation,
    )

    prompt_text = "\n".join(message["content"] for message in fake_chat.messages)
    assert answer == "Generated answer."
    assert sources
    assert personalization.operational_context_applied is False
    assert "Knowledge Context" in prompt_text
    assert "Operational Context" not in prompt_text
    assert "Employee Context" not in prompt_text
    assert instrumentation.context_requirements["include_knowledge"] is True
    assert instrumentation.context_requirements["include_employee"] is False


@pytest.mark.anyio
async def test_operations_only_route_excludes_knowledge_and_employee(monkeypatch) -> None:
    async def fail_search(*_):
        raise AssertionError("knowledge search should not run")

    async def fail_employee(*_, **__):
        raise AssertionError("employee context should not be built")

    async def fake_operations(*_, **__):
        return OperationsContext(
            applied=True,
            text="[Monday Task 1] Urgent task | ID: 1",
            task_count=1,
            board_count=1,
            summary="1 active.",
            original_task_count=3,
            original_chars=100,
            final_chars=35,
        )

    monkeypatch.setattr(knowledge_service, "_search_routed_collections", fail_search)
    monkeypatch.setattr(
        knowledge_service.context_engine,
        "build_employee_context",
        fail_employee,
    )
    monkeypatch.setattr(
        knowledge_service.operations_context_service,
        "build",
        fake_operations,
    )
    monkeypatch.setattr(knowledge_service.ollama_service, "chat", fake_chat)

    instrumentation = AskPerformanceInstrumentation()
    answer, sources, personalization = await answer_with_knowledge(
        question="Which tasks are overdue, and what should be handled first?",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=True,
        current_user=SimpleNamespace(),
        db=None,
        instrumentation=instrumentation,
    )

    prompt_text = "\n".join(message["content"] for message in fake_chat.messages)
    assert answer == "Generated answer."
    assert sources == []
    assert personalization.operational_context_applied is True
    assert "Operational Context" in prompt_text
    assert "Knowledge Context" not in prompt_text
    assert "Employee Context" not in prompt_text
    assert instrumentation.metrics["operational_tasks_final"] == 1


@pytest.mark.anyio
async def test_employee_only_route_excludes_unrelated_context(monkeypatch) -> None:
    async def fail_search(*_):
        raise AssertionError("knowledge search should not run")

    async def fail_operations(*_, **__):
        raise AssertionError("operations context should not be built")

    async def fake_employee(*_, **__):
        return ContextBundle(
            system_context="EMPLOYEE CONTEXT\n- Job title: Producer",
            metadata=ContextMetadata(
                applied=True,
                routed_intent="employee",
                routing_confidence=0.82,
                intelligence_sources=["employee"],
            ),
        )

    monkeypatch.setattr(knowledge_service, "_search_routed_collections", fail_search)
    monkeypatch.setattr(
        knowledge_service.context_engine,
        "build_employee_context",
        fake_employee,
    )
    monkeypatch.setattr(
        knowledge_service.operations_context_service,
        "build",
        fail_operations,
    )
    monkeypatch.setattr(knowledge_service.ollama_service, "chat", fake_chat)

    instrumentation = AskPerformanceInstrumentation()
    answer, sources, personalization = await answer_with_knowledge(
        question="Based on my role and preferences, what should I focus on next?",
        top_k=5,
        category=None,
        assistant="general",
        use_employee_context=True,
        current_user=SimpleNamespace(),
        db=None,
        instrumentation=instrumentation,
    )

    prompt_text = "\n".join(message["content"] for message in fake_chat.messages)
    assert answer == "Generated answer."
    assert sources == []
    assert personalization.applied is True
    assert "Employee Context" in prompt_text
    assert "Knowledge Context" not in prompt_text
    assert "Operational Context" not in prompt_text
