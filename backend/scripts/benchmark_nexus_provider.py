from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.models import AtlasProviderCollectionContext, AtlasProviderRequest
from app.atlas.providers.nexus import NexusGraphStore, NexusProvider, NexusQuery, nexus_graph_to_provider_result


async def main() -> None:
    store = NexusGraphStore()
    provider = NexusProvider(graph_store=store)
    query = NexusQuery(max_entities=16, max_relationships=32, max_depth=2)

    started = perf_counter()
    graph = await store.query(query)
    graph_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    nexus_graph_to_provider_result(graph)
    conversion_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    await provider.collect(
        AtlasProviderRequest(request_id="benchmark-1"),
        AtlasProviderCollectionContext(provider_id="nexus"),
    )
    provider_ms = (perf_counter() - started) * 1000

    print(
        {
            "graph_query_ms": round(graph_ms, 3),
            "conversion_ms": round(conversion_ms, 3),
            "provider_overhead_ms": round(provider_ms, 3),
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
