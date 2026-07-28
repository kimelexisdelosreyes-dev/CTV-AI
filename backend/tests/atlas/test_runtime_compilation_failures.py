import pytest

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .test_compiler_determinism import snapshot
from .test_compiler_validation import _tampered


class ExplodingCompiler(AtlasContextCompiler):
    def compile(self, value): raise RuntimeError("private provider content")


@pytest.mark.asyncio
async def test_invalid_snapshot_preserves_safe_category_and_runtime_ready(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize()
    invalid = _tampered(snapshot())
    with pytest.raises(AtlasRuntimeError) as caught: manager.compile_context(invalid)
    assert caught.value.category == AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID
    assert manager.runtime_state.value == "ready"


@pytest.mark.asyncio
async def test_unexpected_exception_is_sanitized(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler=ExplodingCompiler()); await manager.initialize()
    with pytest.raises(AtlasRuntimeError) as caught: manager.compile_context(snapshot())
    assert caught.value.category == AtlasErrorCategory.COMPILATION_FAILED
    assert "private provider content" not in caught.value.safe_message


@pytest.mark.asyncio
async def test_later_valid_compilation_succeeds_after_invalid(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize()
    with pytest.raises(AtlasRuntimeError): manager.compile_context(_tampered(snapshot()))
    assert manager.compile_context(snapshot()).status == "complete"
