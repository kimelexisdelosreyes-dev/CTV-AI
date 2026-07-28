from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.bootstrap import atlas_runtime_manager
from app.core.config import settings
from app.shadow_mode import AtlasShadowModeService


async def main() -> None:
    settings.ctv_one_atlas_live_enabled = True
    settings.ctv_one_atlas_health_poll_enabled = False
    await atlas_runtime_manager.initialize()
    service = AtlasShadowModeService(atlas_runtime_manager)
    messages = [{"role": "system", "content": "System\n\nMemory\nprior"}, {"role": "user", "content": "benchmark"}]

    started = perf_counter()
    routed, trace, _ = await service.route_messages(
        messages=messages,
        request_id="benchmark-1",
        user_identifier="employee",
        intent="benchmark",
    )
    total_ms = (perf_counter() - started) * 1000
    if trace is None or routed is messages:
        raise SystemExit("live benchmark failed")
    print(
        {
            "atlas_execution_ms": trace.timing_summary.provider_orchestration_ms + trace.timing_summary.compiler_ms,
            "forge_adaptation_ms": trace.timing_summary.adapter_ms,
            "prompt_assembly_ms": trace.timing_summary.comparison_ms,
            "total_overhead_ms": round(total_ms, 3),
        }
    )
    await atlas_runtime_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
