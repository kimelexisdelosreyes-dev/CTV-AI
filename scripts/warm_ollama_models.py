from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import httpx


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import Settings  # noqa: E402


@dataclass(frozen=True)
class WarmupResult:
    model: str
    status: str
    duration_seconds: float


def configured_models(config: Settings) -> list[str]:
    candidates = [
        config.ctv_one_model_reasoning,
        config.ctv_one_model_balanced,
        config.ctv_one_model_operations,
        config.ctv_one_model_knowledge,
        config.ctv_one_model_fast,
        config.ctv_one_model_default,
    ]
    models: list[str] = []
    for model in candidates:
        if model and model not in models:
            models.append(model)
    return models


async def warm_configured_models(
    config: Settings,
    client: httpx.AsyncClient,
    *,
    keep_alive: str,
) -> list[WarmupResult]:
    response = await client.get("/api/tags")
    response.raise_for_status()
    available = {
        item.get("name")
        for item in response.json().get("models", [])
        if item.get("name")
    }
    results: list[WarmupResult] = []
    for model in configured_models(config):
        if model not in available:
            results.append(WarmupResult(model, "not_installed", 0.0))
            continue
        started = perf_counter()
        response = await client.post(
            "/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Reply with OK.",
                    }
                ],
                "stream": False,
                "think": False,
                "keep_alive": keep_alive,
                "options": {"num_predict": 2},
            },
        )
        response.raise_for_status()
        results.append(
            WarmupResult(
                model=model,
                status="warmed",
                duration_seconds=round(perf_counter() - started, 3),
            )
        )
    return results


async def run() -> int:
    config = Settings(_env_file=BACKEND / ".env")
    keep_alive = os.getenv("CTV_ONE_MODEL_WARMUP_KEEP_ALIVE", "10m")
    try:
        async with httpx.AsyncClient(
            base_url=config.ollama_base_url,
            timeout=config.request_timeout_seconds,
        ) as client:
            results = await warm_configured_models(
                config,
                client,
                keep_alive=keep_alive,
            )
    except httpx.HTTPError:
        print("Ollama is unavailable; model warmup skipped.")
        return 0

    for result in results:
        print(
            f"{result.model}: {result.status} "
            f"({result.duration_seconds:.3f}s)"
        )
    print(
        "Warmup order is a run-relative hint only; it does not prove model residency."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
