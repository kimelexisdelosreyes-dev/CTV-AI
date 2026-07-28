from copy import deepcopy

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import AtlasAIRPackage, AtlasClassification
from .test_compiler_determinism import snapshot


def _duplicate_graph():
    compiler = AtlasContextCompiler(); source = snapshot(records=1, providers=1)
    inputs, *_ = compiler._select(source)
    air, _ = compiler._normalize(source, inputs)
    first = air.records[0]
    second = first.model_copy(update={"air_id": "air-duplicate000000000000000"})
    graph, _ = compiler._graph(AtlasAIRPackage(records=(first, second)))
    return compiler, graph


def test_exact_duplicate_removed():
    compiler, graph = _duplicate_graph(); optimized, _ = compiler._deduplicate(graph)
    assert len(optimized.nodes) == 1


def test_duplicate_emits_exclusion_decision():
    compiler, graph = _duplicate_graph(); _, decisions = compiler._deduplicate(graph)
    assert len(decisions) == 1 and decisions[0].reason_categories == ("exact_duplicate",)


def test_orphan_relationships_removed():
    compiler, graph = _duplicate_graph(); optimized, _ = compiler._deduplicate(graph)
    assert all(r.source_node_id in {n.node_id for n in optimized.nodes} for r in optimized.relationships)


def test_provenance_retained():
    compiler, graph = _duplicate_graph(); optimized, _ = compiler._deduplicate(graph)
    assert optimized.nodes[0].provenance == graph.nodes[0].provenance


def test_classification_retained():
    compiler, graph = _duplicate_graph(); optimized, _ = compiler._deduplicate(graph)
    assert optimized.nodes[0].classification == AtlasClassification.INTERNAL


def test_no_semantic_rewriting_or_input_mutation():
    compiler, graph = _duplicate_graph(); before = deepcopy(graph.nodes)
    optimized, _ = compiler._deduplicate(graph)
    assert graph.nodes == before and optimized.nodes[0].label == graph.nodes[0].label


def test_optimizer_is_deterministic_and_idempotent():
    compiler, graph = _duplicate_graph(); once, _ = compiler._deduplicate(graph); twice, decisions = compiler._deduplicate(once)
    assert twice == once and decisions == ()
