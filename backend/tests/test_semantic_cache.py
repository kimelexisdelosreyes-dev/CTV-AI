import asyncio
import uuid

from app.core.context_requirements import ContextRequirements
from app.services.semantic_cache import (
    SemanticCacheService,
    _cosine,
    normalize_query,
)
from app.services import semantic_cache as cache_module


def requirements(**overrides) -> ContextRequirements:
    values = {
        "include_knowledge": True,
        "include_operations": False,
        "include_employee": False,
        "include_history": False,
        "knowledge_collections": ["company-policies"],
    }
    values.update(overrides)
    return ContextRequirements(**values)


def test_normalized_exact_match_ignores_case_punctuation_and_whitespace() -> None:
    assert normalize_query("  Leave, POLICY?!  ") == normalize_query("leave policy")


def test_cosine_threshold_inputs_distinguish_match_and_miss() -> None:
    assert _cosine([1.0, 0.0], [0.99, 0.01]) > 0.94
    assert _cosine([1.0, 0.0], [0.0, 1.0]) < 0.94


def test_bypass_phrase_skips_cache() -> None:
    service = SemanticCacheService()
    lookup = asyncio.run(service.build_lookup(
        question="Please check again and refresh the leave policy",
        route_intent="policy",
        requirements=requirements(),
        current_user_id=uuid.uuid4(),
        conversation_id=None,
        assistant="general",
        category=None,
    ))
    assert lookup.eligible is False
    assert lookup.skip_reason == "bypass_phrase"


def test_complex_reasoning_skips_cache() -> None:
    service = SemanticCacheService()
    lookup = asyncio.run(service.build_lookup(
        question="Analyze the strategic tradeoffs in this policy",
        route_intent="policy",
        requirements=requirements(),
        current_user_id=uuid.uuid4(),
        conversation_id=None,
        assistant="general",
        category=None,
    ))
    assert lookup.skip_reason == "complex_reasoning"


def test_employee_and_conversation_context_are_isolated_and_ineligible() -> None:
    service = SemanticCacheService()
    first_user = uuid.uuid4()
    second_user = uuid.uuid4()
    employee_one = asyncio.run(service.build_lookup(
        question="What should I focus on?",
        route_intent="employee",
        requirements=requirements(include_employee=True),
        current_user_id=first_user,
        conversation_id=None,
        assistant="general",
        category=None,
    ))
    employee_two = asyncio.run(service.build_lookup(
        question="What should I focus on?",
        route_intent="employee",
        requirements=requirements(include_employee=True),
        current_user_id=second_user,
        conversation_id=None,
        assistant="general",
        category=None,
    ))
    conversation_id = uuid.uuid4()
    conversation = asyncio.run(service.build_lookup(
        question="What did we decide?",
        route_intent="policy",
        requirements=requirements(include_history=True),
        current_user_id=first_user,
        conversation_id=conversation_id,
        assistant="general",
        category=None,
    ))
    assert employee_one.scope_key != employee_two.scope_key
    assert employee_one.skip_reason == employee_two.skip_reason == "employee_context"
    assert conversation.scope_key == f"conversation:{conversation_id}"
    assert conversation.skip_reason == "conversation_context"


def test_changed_source_revision_changes_invalidation_and_exact_key(monkeypatch) -> None:
    service = SemanticCacheService()
    states = iter([("ops-a", "knowledge-a"), ("ops-b", "knowledge-a")])

    async def state(_):
        return next(states)

    monkeypatch.setattr(service, "_state_fingerprints", state)
    kwargs = {
        "question": "What are today's priorities?",
        "route_intent": "operations",
        "requirements": requirements(include_operations=True),
        "current_user_id": uuid.uuid4(),
        "conversation_id": None,
        "assistant": "general",
        "category": None,
    }
    async def build_pair():
        return await service.build_lookup(**kwargs), await service.build_lookup(**kwargs)

    first, second = asyncio.run(build_pair())
    assert first.invalidation_fingerprint != second.invalidation_fingerprint
    assert first.exact_key != second.exact_key


def test_operations_fingerprint_uses_active_content_hash(monkeypatch) -> None:
    class Result:
        def first(self):
            return ("stable-content-hash",)

    class Session:
        async def execute(self, statement):
            rendered = str(statement)
            assert "operations_snapshots.status" in rendered
            assert "content_hash" in rendered
            return Result()

    class SessionContext:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(cache_module, "AsyncSessionLocal", SessionContext)
    operations, knowledge = asyncio.run(
        SemanticCacheService()._state_fingerprints(("operations",))
    )
    assert operations == "stable-content-hash"
    assert knowledge is None
