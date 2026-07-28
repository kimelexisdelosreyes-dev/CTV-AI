from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.bootstrap import atlas_runtime_manager
from app.shadow_mode import AtlasShadowModeService
from app.core.config import settings


async def main() -> None:
    settings.ctv_one_atlas_shadow_enabled = True
    settings.ctv_one_atlas_health_poll_enabled = False
    await atlas_runtime_manager.initialize()
    service = AtlasShadowModeService(atlas_runtime_manager)
    started = perf_counter()
    trace = await service.execute(
        production_prompt="System\nbenchmark\n\nMemory\nbenchmark",
        request_id="benchmark-1",
        intent="benchmark",
    )
    total_ms = (perf_counter() - started) * 1000
    if trace is None:
        raise SystemExit("shadow benchmark failed")
    print(
        {
            "provider_ms": trace.timing_summary.provider_orchestration_ms,
            "compiler_ms": trace.timing_summary.compiler_ms,
            "adapter_ms": trace.timing_summary.adapter_ms,
            "trace_ms": trace.timing_summary.trace_ms,
            "comparison_ms": trace.timing_summary.comparison_ms,
            "total_ms": round(total_ms, 3),
        }
    )
    await atlas_runtime_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
