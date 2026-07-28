from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import random

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import AtlasCompilationSnapshot, AtlasCompilerPolicy, AtlasContextRequest, AtlasProvenance, AtlasProviderInputSnapshot, AtlasProviderSelectionEntry, AtlasProviderSelectionPlan


def snapshot(records=6, providers=2):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    inputs = []
    entries = []
    for provider_index in range(providers):
        provider = f"provider_{provider_index}"
        provenance = AtlasProvenance(provider_id=provider, source_id=f"source-{provider_index}", source_type="fixture", source_sequence=provider_index, collected_at=now, original_reference=f"reference-{provider_index}", content_digest=(str(provider_index % 10) * 64))
        values = tuple({"id": f"{provider}-{item}", "title": f"title-{item}", "content": "x" * 24, "confidence_points": item} for item in range(records))
        inputs.append(AtlasProviderInputSnapshot(provider_id=provider, provider_version="1.0", provider_contract_version="1.0", result_schema_version="1.0", source_sequence=provider_index, collected_at=now, provenance=provenance, records=values))
        entries.append(AtlasProviderSelectionEntry(provider_id=provider, selected=True, ordinal=provider_index))
    return AtlasCompilationSnapshot(request=AtlasContextRequest(request_id="request-1", intent="summary"), compiler_policy=AtlasCompilerPolicy(max_total_nodes=128, max_nodes_per_provider=128), provider_selection_plan=AtlasProviderSelectionPlan(entries=tuple(entries)), provider_inputs=tuple(inputs), compilation_time=now, source_configuration_fingerprint="b" * 64)


def test_100_repeated_and_50_permuted_runs_are_identical():
    original = snapshot()
    compiler = AtlasContextCompiler()
    baseline = compiler.compile(original).deterministic_digest
    for _ in range(100):
        assert compiler.compile(original).deterministic_digest == baseline
    source = list(original.provider_inputs)
    for seed in range(50):
        shuffled = source[:]; random.Random(seed).shuffle(shuffled)
        candidate = AtlasCompilationSnapshot(request=original.request, compiler_policy=original.compiler_policy, provider_selection_plan=original.provider_selection_plan, provider_inputs=tuple(shuffled), compilation_time=original.compilation_time, source_configuration_fingerprint=original.source_configuration_fingerprint)
        assert compiler.compile(candidate).deterministic_digest == baseline


def test_concurrent_compilations_are_isolated():
    source = snapshot()
    with ThreadPoolExecutor(max_workers=10) as executor:
        outputs = list(executor.map(lambda _: AtlasContextCompiler().compile(source).deterministic_digest, range(20)))
    assert len(set(outputs)) == 1


def test_large_workload_is_bounded_and_provenanced():
    result = AtlasContextCompiler().compile(snapshot(records=84, providers=6))
    assert len(result.graph_nodes) <= 128
    assert result.context_package.serialized_bytes() <= 131_072
    assert all(node.provenance for node in result.graph_nodes)
