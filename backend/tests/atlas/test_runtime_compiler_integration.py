import pytest

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .test_compiler_determinism import snapshot


class CountingCompiler(AtlasContextCompiler):
    def __init__(self): self.calls = 0
    def compile(self, value):
        self.calls += 1
        return super().compile(value)


@pytest.mark.asyncio
async def test_injected_compiler_is_owned_once_and_reused(atlas_settings):
    compiler = CountingCompiler(); manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler=compiler)
    await manager.initialize(); first = manager.compile_context(snapshot()); second = manager.compile_context(snapshot())
    assert manager.compiler is compiler and compiler.calls == 2
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.asyncio
async def test_runtime_and_direct_outputs_are_byte_identical(atlas_settings):
    source = snapshot(); compiler = AtlasContextCompiler(); manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler=compiler)
    await manager.initialize(); direct = compiler.compile(source); managed = manager.compile_context(source)
    assert direct.canonical_bytes() == managed.canonical_bytes()
    assert direct.context_package.package_fingerprint == managed.context_package.package_fingerprint


@pytest.mark.asyncio
async def test_fifty_runtime_compilations_match_direct_bytes(atlas_settings):
    source = snapshot(); compiler = AtlasContextCompiler(); manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler=compiler)
    await manager.initialize(); expected = compiler.compile(source).canonical_bytes()
    assert all(manager.compile_context(source).canonical_bytes() == expected for _ in range(50))


@pytest.mark.asyncio
async def test_snapshot_remains_immutable_after_runtime_compile(atlas_settings):
    source = snapshot(); before = source.canonical_bytes(); manager = AtlasRuntimeManager(AtlasProviderRegistry())
    await manager.initialize(); manager.compile_context(source)
    assert source.canonical_bytes() == before


@pytest.mark.asyncio
async def test_lazy_compiler_factory_runs_once(atlas_settings):
    created = []
    def factory(): created.append(1); return AtlasContextCompiler()
    manager = AtlasRuntimeManager(AtlasProviderRegistry(), compiler_factory=factory)
    await manager.initialize(); await manager.initialize(); manager.compile_context(snapshot())
    assert len(created) == 1
