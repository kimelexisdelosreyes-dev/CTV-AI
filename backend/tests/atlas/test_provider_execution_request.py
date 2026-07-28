import pytest
from pydantic import ValidationError

from app.atlas.provider_orchestration import AtlasProviderExecutionPlan
from .provider_orchestration_fixtures import execution_request


def test_request_is_immutable_canonical_and_fingerprinted():
    request = execution_request(AtlasProviderExecutionPlan(provider_id="z_provider"), AtlasProviderExecutionPlan(provider_id="a_provider"))
    assert [item.provider_id for item in request.selected_provider_plans] == ["a_provider", "z_provider"]
    assert request.deterministic_fingerprint() == request.deterministic_fingerprint()
    with pytest.raises(ValidationError): request.request_id = "changed"


def test_duplicate_provider_plans_rejected():
    plan = AtlasProviderExecutionPlan(provider_id="fixture_provider")
    with pytest.raises(ValidationError): execution_request(plan, plan)


def test_unsafe_and_arbitrary_metadata_rejected():
    with pytest.raises((ValidationError, ValueError)): execution_request().model_copy(update={"caller_metadata":{"secret":"x"}}).__class__(**{**execution_request().model_dump(), "caller_metadata":{"secret":"x"}})
    with pytest.raises((ValidationError, TypeError)): AtlasProviderExecutionPlan(provider_id="fixture_provider", provider_config={"value": object()})


def test_caller_timestamp_is_retained():
    request = execution_request(); assert request.compilation_time.isoformat() == "2026-01-01T00:00:00+00:00"
