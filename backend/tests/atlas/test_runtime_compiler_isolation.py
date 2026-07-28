import inspect

import pytest

from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .test_compiler_determinism import snapshot


@pytest.mark.asyncio
async def test_compile_context_does_not_use_registry_or_provider_hooks(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize()
    class Bomb:
        def __getattr__(self, name): raise AssertionError(name)
    manager.registry = Bomb()
    assert manager.compile_context(snapshot()).status == "complete"


def test_compile_context_has_no_nexus_forge_database_or_inference_imports():
    source = inspect.getsource(__import__("app.atlas.runtime_manager", fromlist=["*"]))
    for prohibited in ("app.supervisor", "app.agents", "app.db", "ollama", "inference_queue"):
        assert prohibited not in source
