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
from app.shadow_mode import AtlasShadowModeService, CanaryPolicy


async def main() -> None:
    settings.ctv_one_atlas_canary_enabled = True
    settings.ctv_one_atlas_canary_users = "technical_manager"
    settings.ctv_one_atlas_health_poll_enabled = False
    await atlas_runtime_manager.initialize()
    service = AtlasShadowModeService(atlas_runtime_manager)
    messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "benchmark"}]

    policy_started = perf_counter()
    CanaryPolicy().decide("technical_manager")
    policy_ms = (perf_counter() - policy_started) * 1000

    allowlist_started = perf_counter()
    CanaryPolicy(canary_enabled=True, canary_users=("technical_manager",)).decide("technical_manager")
    allowlist_ms = (perf_counter() - allowlist_started) * 1000

    total_started = perf_counter()
    _, trace, _ = await service.route_messages(
        messages=messages,
        request_id="benchmark-1",
        user_identifier="technical_manager",
        intent="benchmark",
    )
    total_ms = (perf_counter() - total_started) * 1000
    if trace is None:
        raise SystemExit("canary benchmark failed")

    fallback_started = perf_counter()
    await service.route_messages(
        messages=messages,
        request_id="benchmark-2",
        user_identifier="normal_user",
        intent="benchmark",
    )
    fallback_ms = (perf_counter() - fallback_started) * 1000

    print(
        {
            "policy_ms": round(policy_ms, 3),
            "allowlist_ms": round(allowlist_ms, 3),
            "atlas_execution_ms": trace.timing_summary.total_ms,
            "fallback_ms": round(fallback_ms, 3),
            "total_overhead_ms": round(total_ms, 3),
        }
    )
    await atlas_runtime_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
