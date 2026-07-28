import pytest

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.context_package import AtlasContextPackage, validate_context_package
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from .test_compiler_determinism import snapshot


def _artifacts():
    compiler = AtlasContextCompiler(); source = snapshot(records=2, providers=1)
    inputs, select, warnings = compiler._select(source); air, air_d = compiler._normalize(source, inputs)
    graph, graph_d = compiler._graph(air); graph, dedup_d = compiler._deduplicate(graph)
    conflicts, conflict_d = compiler._conflicts(graph); scores, score_d = compiler._score(source, graph, conflicts)
    ranked, rank_d = compiler._rank(scores); nodes, rels, usage, budget, budget_d = compiler._budget(source, graph, ranked)
    manifest = compiler._manifest(source, select + air_d + graph_d + dedup_d + conflict_d + score_d + rank_d + budget_d, inputs, conflicts, usage, warnings)
    package = compiler._package(source, inputs, nodes, rels, conflicts, usage, manifest, warnings, len(budget))
    return source, manifest, package


def test_package_is_v11_reference_only():
    _, _, package = _artifacts(); assert package.contract_version == "1.1" and package.manifest is None and package.manifest_reference


def test_empty_package_compatibility():
    assert AtlasContextPackage(request_id="request-1").nodes == ()


def test_supplied_created_at_and_canonical_providers():
    source, _, package = _artifacts(); assert package.created_at == source.compilation_time and package.selected_provider_ids == ("provider_0",)


def test_snapshot_policy_and_manifest_digests():
    source, manifest, package = _artifacts()
    assert package.snapshot_fingerprint == source.snapshot_fingerprint
    assert package.compiler_policy_fingerprint == source.compiler_policy.policy_fingerprint
    assert package.manifest_reference.manifest_digest == manifest.computed_digest


def test_budget_usage_and_optimization_statistics():
    _, _, package = _artifacts(); assert package.budgets.node_count == len(package.nodes) and package.optimization.omitted_item_count == 0


def test_serialized_bytes_and_fingerprint_verify():
    _, _, package = _artifacts(); assert package.serialized_bytes() == len(package.deterministic_json().encode("utf-8")) and package.package_fingerprint == package.computed_fingerprint()


def test_runtime_metrics_do_not_change_fingerprint():
    _, _, package = _artifacts(); changed = package.model_copy(update={"metrics": package.metrics.__class__({"latency_ms": 9})})
    assert changed.computed_fingerprint() == package.computed_fingerprint()


def test_package_nested_metadata_is_immutable_by_copy():
    _, _, package = _artifacts(); value = package.metadata.to_python(); value = {"changed": True}
    assert package.metadata.to_python() != value


def test_invalid_relationship_reference_rejected():
    with pytest.raises(AtlasRuntimeError):
        validate_context_package({"request_id":"request-1", "relationships":[{"relationship_type":"related_to", "source_node_id":"missing", "target_node_id":"missing"}]})


def test_meaningful_content_changes_fingerprint_and_repeat_is_stable():
    _, _, first = _artifacts(); _, _, second = _artifacts()
    changed = first.model_copy(update={"request_id":"request-2", "package_fingerprint":""})
    assert first.package_fingerprint == second.package_fingerprint
    assert changed.computed_fingerprint() != first.computed_fingerprint()
