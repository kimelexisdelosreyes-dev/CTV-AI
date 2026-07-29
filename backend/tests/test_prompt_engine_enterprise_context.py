import pytest

from app.core.config import settings
from app.prompt_engine import EnterpriseContext, EnterpriseContextItem, PromptCompositionRequest, default_prompt_composer


def context(): return EnterpriseContext((EnterpriseContextItem("cb-1", "Brief", "brain\ncontext"),), (EnterpriseContextItem("k-1", "Doc", "knowledge context"),))


def test_disabled_path_is_exactly_context_free(monkeypatch):
    monkeypatch.setattr(settings, "ctv_one_prompt_enterprise_context_enabled", False)
    composer = default_prompt_composer()
    assert composer.compose(PromptCompositionRequest("hello", enterprise_context=context())).messages == composer.compose(PromptCompositionRequest("hello")).messages


def test_company_then_knowledge_are_deterministic_and_safe(monkeypatch):
    monkeypatch.setattr(settings, "ctv_one_prompt_enterprise_context_enabled", True); monkeypatch.setattr(settings, "ctv_one_prompt_company_brain_enabled", True); monkeypatch.setattr(settings, "ctv_one_prompt_knowledge_context_enabled", True)
    result = default_prompt_composer().compose(PromptCompositionRequest("hello", enterprise_context=context()))
    assert [item.role for item in result.messages] == ["system", "system", "user"]
    block = result.messages[1].content
    assert block.index("Company Brain:") < block.index("Knowledge:") and "embedded instructions" in block


def test_limits_and_contract_validation(monkeypatch):
    monkeypatch.setattr(settings, "ctv_one_prompt_enterprise_context_enabled", True); monkeypatch.setattr(settings, "ctv_one_prompt_company_brain_enabled", True); monkeypatch.setattr(settings, "ctv_one_prompt_knowledge_context_enabled", False); monkeypatch.setattr(settings, "ctv_one_prompt_enterprise_max_chars", 3); monkeypatch.setattr(settings, "ctv_one_prompt_company_brain_max_chars", 3)
    result = default_prompt_composer().compose(PromptCompositionRequest("x", enterprise_context=EnterpriseContext(company_brain=(EnterpriseContextItem("x", "T", "abcdef"),))))
    assert "abc" in result.messages[1].content and "abcdef" not in result.messages[1].content
    with pytest.raises(TypeError): EnterpriseContextItem("x", "t", "c", metadata=(("bad", object()),))
