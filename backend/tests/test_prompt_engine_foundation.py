import json
from dataclasses import FrozenInstanceError

import pytest

from app.prompt_engine import PROMPT_ENGINE_VERSION, PromptComposer, PromptCompositionRequest, PromptMessage, PromptRole, PromptStageRegistry
from app.prompt_engine.stages import ConversationStage, ProviderFormattingStage, SystemPromptStage


def composer() -> PromptComposer:
    return PromptComposer(PromptStageRegistry((ConversationStage(), SystemPromptStage(), ProviderFormattingStage())))


def request() -> PromptCompositionRequest:
    return PromptCompositionRequest("latest user", (PromptMessage("user", "earlier user"), PromptMessage("assistant", "earlier answer")), "model-x", metadata=(("language", "en"),))


def test_contracts_are_immutable_serializable_and_provider_neutral():
    value = request()
    assert PROMPT_ENGINE_VERSION == "1.1"
    with pytest.raises(FrozenInstanceError): value.user_input = "changed"
    with pytest.raises(TypeError): PromptCompositionRequest("x", [])
    result = composer().compose(value)
    serialized = json.dumps(result.to_dict())
    assert serialized


def test_registry_is_ordered_immutable_and_rejects_duplicate_stages():
    registry = PromptStageRegistry((ConversationStage(), SystemPromptStage(), ProviderFormattingStage()))
    assert registry.stage_ids == ("conversation", "system-prompt", "provider-format")
    with pytest.raises(ValueError): PromptStageRegistry((ConversationStage(), ConversationStage()))
    with pytest.raises(TypeError): PromptStageRegistry([ConversationStage()])


def test_composition_is_deterministic_and_preserves_conversation_order():
    first, second = composer().compose(request()), composer().compose(request())
    assert first == second
    assert [message.role for message in first.messages] == ["system", "user", "assistant", "user"]
    assert [message.content for message in first.messages[1:]] == ["earlier user", "earlier answer", "latest user"]


def test_diagnostics_are_safe_and_report_stage_order_without_prompt_text():
    instance = composer(); result = instance.compose(request())
    trace, statistics = instance.last_trace, instance.last_statistics
    assert result.diagnostics == () and trace is not None and statistics is not None
    serialized = json.dumps(trace.__dict__)
    assert trace.stage_order == ("conversation", "system-prompt", "provider-format")
    assert statistics.stage_count == 3 and statistics.warning_count == 0
    for secret in ("latest user", "earlier answer"):
        assert secret not in serialized
