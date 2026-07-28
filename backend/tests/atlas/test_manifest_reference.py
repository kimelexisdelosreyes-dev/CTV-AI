from app.atlas.compiler import AtlasContextCompiler
from .test_compiler_determinism import snapshot


def test_package_references_the_full_manifest_without_embedding_it():
    result = AtlasContextCompiler().compile(snapshot(records=20, providers=2))
    reference = result.context_package.manifest_reference
    assert result.context_package.manifest is None
    assert reference is not None
    assert reference.manifest_digest == result.manifest.computed_digest
    assert reference.decision_count == len(result.manifest.entries)
