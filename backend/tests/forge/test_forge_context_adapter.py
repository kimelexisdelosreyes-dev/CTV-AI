from app.forge.context_adapter import ForgeContextAdapter


def test_adapter_preserves_order_and_atlas_values(atlas_package) -> None:
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    assert tuple(block.node_id for block in window.context_blocks) == tuple(node.node_id for node in atlas_package.nodes)
    for block, node, evidence in zip(window.context_blocks, atlas_package.nodes, atlas_package.evidence):
        assert block.title == node.label
        assert block.content == evidence.excerpt
        assert block.classification == node.classification
        assert block.confidence == node.score_points
        assert block.provenance == node.provenance
        assert block.citations == (atlas_package.citations[node.ordinal],)


def test_adapter_preserves_package_and_manifest_references(atlas_package) -> None:
    window = ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    assert window.package_fingerprint == atlas_package.package_fingerprint
    assert window.manifest_reference == atlas_package.manifest_reference
