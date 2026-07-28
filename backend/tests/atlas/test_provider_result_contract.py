import pytest
from pydantic import ValidationError

from app.atlas.models import AtlasProviderResult
from app.atlas.provider_orchestration import AtlasProviderOrchestrator, AtlasValidatedProviderResult


def test_valid_result_is_deeply_immutable_and_stable():
    raw = AtlasProviderResult(provider_id="fixture_provider", data={"records":[{"id":"one", "content":"x"}]})
    result = AtlasProviderOrchestrator._validate_result(raw, "1.0")
    changed = result.records[0].to_python(); changed["content"] = "changed"
    assert result.records[0].to_python()["content"] == "x"
    assert len(result.provider_result_fingerprint) == 64


def test_duplicate_record_ids_rejected():
    with pytest.raises(ValidationError): AtlasValidatedProviderResult(provider_id="fixture_provider", provider_contract_version="1.0", result_schema_version="1.0", status="success", records=({"id":"same"},{"id":"same"}))


def test_unsafe_metadata_and_objects_rejected():
    with pytest.raises((ValidationError, ValueError)): AtlasValidatedProviderResult(provider_id="fixture_provider", provider_contract_version="1.0", result_schema_version="1.0", status="success", source_metadata={"credential":"x"})
    with pytest.raises((ValidationError, TypeError)): AtlasValidatedProviderResult(provider_id="fixture_provider", provider_contract_version="1.0", result_schema_version="1.0", status="success", records=({"value":object()},))


def test_record_and_relation_limits_enforced():
    with pytest.raises(ValidationError): AtlasValidatedProviderResult(provider_id="fixture_provider", provider_contract_version="1.0", result_schema_version="1.0", status="success", records=tuple({"id":str(i)} for i in range(257)))
