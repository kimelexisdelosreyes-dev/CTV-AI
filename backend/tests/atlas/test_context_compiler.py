from datetime import datetime, timezone

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import AtlasCompilationSnapshot, AtlasCompilerPolicy, AtlasContextRequest, AtlasProvenance, AtlasProviderInputSnapshot, AtlasProviderSelectionEntry, AtlasProviderSelectionPlan


def test_compiler_is_pure_and_deterministic():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    provenance = AtlasProvenance(provider_id="fixture_provider", source_id="source-1", source_type="fixture", source_sequence=0, collected_at=now, original_reference="reference-1", content_digest="a" * 64)
    source = AtlasProviderInputSnapshot(provider_id="fixture_provider", provider_version="1.0", provider_contract_version="1.0", result_schema_version="1.0", source_sequence=0, collected_at=now, provenance=provenance, records=({"id":"one", "title":"One", "content":"content", "confidence_points":10},))
    snapshot = AtlasCompilationSnapshot(request=AtlasContextRequest(request_id="request-1", intent="summary"), compiler_policy=AtlasCompilerPolicy(), provider_selection_plan=AtlasProviderSelectionPlan(entries=(AtlasProviderSelectionEntry(provider_id="fixture_provider", selected=True, ordinal=0),)), provider_inputs=(source,), compilation_time=now, source_configuration_fingerprint="b" * 64)
    first = AtlasContextCompiler().compile(snapshot)
    second = AtlasContextCompiler().compile(snapshot)
    assert first.deterministic_digest == second.deterministic_digest
    assert first.context_package.package_fingerprint == second.context_package.package_fingerprint
    assert first.context_package.created_at == now
