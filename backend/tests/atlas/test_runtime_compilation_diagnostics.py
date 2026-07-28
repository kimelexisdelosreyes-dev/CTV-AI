import pytest

from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from .test_compiler_determinism import snapshot


@pytest.mark.asyncio
async def test_diagnostics_expose_bounded_compiler_state(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); manager.compile_context(snapshot())
    status = await manager.status()
    assert status["compiler_available"] is True and status["compiler_readiness"] == "ready"
    assert status["compiler_contract_version"] == "1.0" and status["manifest_version"] == "1.0"
    assert status["compilation_concurrency_limit"] == 4
    assert status["compilation"]["compilation_successes"] == 1


@pytest.mark.asyncio
async def test_diagnostics_contain_no_compiler_artifacts_or_secrets(atlas_settings):
    manager = AtlasRuntimeManager(AtlasProviderRegistry()); await manager.initialize(); manager.compile_context(snapshot())
    text = str(await manager.status()).lower()
    for prohibited in ("normalized_content", "air-", "decision-", "credential", "password", "database_url"):
        assert prohibited not in text
