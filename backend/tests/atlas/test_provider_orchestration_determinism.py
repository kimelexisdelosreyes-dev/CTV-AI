import pytest

from app.atlas.models import AtlasProviderResult
from app.atlas.provider_orchestration import AtlasProviderExecutionPlan
from .provider_orchestration_fixtures import CollectionProvider, execution_request, runtime_with


@pytest.mark.asyncio
async def test_100_repeated_orchestrations_are_identical(atlas_settings):
    manager = runtime_with(CollectionProvider()); await manager.initialize()
    outputs = [await manager.execute_provider_plan(execution_request()) for _ in range(100)]
    assert len({item.compilation_snapshot.canonical_bytes() for item in outputs}) == 1
    assert len({item.compilation_result.deterministic_digest for item in outputs}) == 1


@pytest.mark.asyncio
async def test_50_record_order_permutations_are_identical(atlas_settings):
    provider = CollectionProvider(); manager = runtime_with(provider); await manager.initialize(); digests = set()
    for index in range(50):
        records = [{"id":"a", "content":"A"},{"id":"b", "content":"B"}]
        if index % 2: records.reverse()
        provider.result = AtlasProviderResult(provider_id="fixture_provider", data={"records":records})
        digests.add((await manager.execute_provider_plan(execution_request())).compilation_result.deterministic_digest)
    assert len(digests) == 1


@pytest.mark.asyncio
async def test_50_completion_order_permutations_are_identical(atlas_settings):
    first = CollectionProvider("first_provider"); second = CollectionProvider("second_provider")
    manager = runtime_with(first, second); await manager.initialize(); outputs = set()
    request = execution_request(
        AtlasProviderExecutionPlan(provider_id="first_provider", capabilities=("fixture_context",)),
        AtlasProviderExecutionPlan(provider_id="second_provider", capabilities=("fixture_context",)),
    )
    for index in range(50):
        first.delay, second.delay = ((0.001, 0) if index % 2 else (0, 0.001))
        outcome = await manager.execute_provider_plan(request)
        outputs.add((outcome.compilation_snapshot.canonical_bytes(), outcome.compilation_result.deterministic_digest))
    assert len(outputs) == 1
