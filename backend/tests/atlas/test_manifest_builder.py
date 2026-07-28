from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler.compiler import _decision
from app.atlas.compiler_contracts import AtlasBudgetUsage, AtlasCompilerStage, AtlasSelectionAction
from .test_compiler_determinism import snapshot


def _manifest():
    compiler = AtlasContextCompiler(); source = snapshot(records=1, providers=1)
    inputs, select, warnings = compiler._select(source)
    decision = _decision(AtlasCompilerStage.BUDGET, "node-1", AtlasSelectionAction.SELECTED, "budget_selected", "provider_0")
    return compiler._manifest(source, select + (decision,), inputs, (), AtlasBudgetUsage(nodes=1), warnings)


def test_manifest_creation_and_request_id():
    value = _manifest(); assert value.request_id == "request-1"


def test_snapshot_and_policy_fingerprints():
    value = _manifest(); source = snapshot(records=1, providers=1)
    assert value.snapshot_fingerprint == source.snapshot_fingerprint
    assert value.compiler_policy_fingerprint == source.compiler_policy.policy_fingerprint


def test_selected_and_excluded_providers():
    value = _manifest(); assert value.selected_provider_ids == ("provider_0",) and value.excluded_provider_ids == ()


def test_decisions_are_canonically_ordered():
    value = _manifest(); assert value.entries == tuple(sorted(value.entries, key=lambda item: item.decision_id))


def test_stage_summaries_cover_all_stages():
    value = _manifest(); assert {item.stage for item in value.stage_summaries} == set(AtlasCompilerStage)


def test_decision_ids_and_reasons_are_stable():
    first = _manifest(); second = _manifest()
    assert [(d.decision_id, d.reason_categories) for d in first.entries] == [(d.decision_id, d.reason_categories) for d in second.entries]


def test_manifest_contains_no_unsafe_explanation_fields():
    text = _manifest().canonical_json().lower()
    assert all(term not in text for term in ("chain-of-thought", "traceback", "credential", "password"))


def test_manifest_digest_and_bytes_are_repeatable():
    first = _manifest(); second = _manifest()
    assert first.deterministic_digest == first.computed_digest
    assert first.canonical_bytes() == second.canonical_bytes()
