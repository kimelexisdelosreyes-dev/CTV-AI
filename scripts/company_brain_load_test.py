"""Local, credential-free-by-default load client for Company Brain admission tests."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from collections import Counter
from dataclasses import dataclass
from time import perf_counter

import httpx


DEFAULT_PROMPTS = (
    "What is our leave policy?",
    "What should the company prioritize today?",
    "Explain the equipment approval process.",
)


@dataclass(frozen=True)
class LoadResult:
    success: bool
    rejected: bool
    timed_out: bool
    cache_hit: bool
    latency_ms: float
    queue_wait_ms: float
    queue_depth: int
    model: str | None
    priority: str | None


def percentile(values: list[float], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * proportion), len(ordered) - 1)
    return ordered[index]


def summarize(results: list[LoadResult], duration_seconds: float) -> dict[str, object]:
    latencies = [item.latency_ms for item in results]
    queue_waits = [item.queue_wait_ms for item in results]
    return {
        "total_requests": len(results),
        "success_count": sum(item.success for item in results),
        "rejection_count": sum(item.rejected for item in results),
        "timeout_count": sum(item.timed_out for item in results),
        "cache_hit_count": sum(item.cache_hit for item in results),
        "mean_latency_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "median_latency_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "average_queue_wait_ms": (
            round(statistics.fmean(queue_waits), 3) if queue_waits else 0.0
        ),
        "maximum_queue_depth": max(
            (item.queue_depth for item in results),
            default=0,
        ),
        "throughput_requests_per_second": round(
            len(results) / duration_seconds if duration_seconds > 0 else 0.0,
            3,
        ),
        "model_distribution": dict(
            Counter(item.model or "unknown" for item in results)
        ),
        "priority_distribution": dict(
            Counter(item.priority or "none" for item in results)
        ),
    }


def _number(headers: httpx.Headers, name: str) -> float:
    try:
        return float(headers.get(name, "0"))
    except ValueError:
        return 0.0


async def non_streaming_request(
    client: httpx.AsyncClient,
    endpoint: str,
    question: str,
) -> LoadResult:
    started = perf_counter()
    try:
        response = await client.post(endpoint, json={"question": question})
        latency_ms = (perf_counter() - started) * 1000
    except httpx.TimeoutException:
        return LoadResult(False, False, True, False, 0.0, 0.0, 0, None, None)
    category = response.headers.get("X-Error-Category")
    return LoadResult(
        success=response.is_success,
        rejected=response.status_code in {429, 503} and category in {
            "queue_full",
            "per_user_queue_limit",
            "service_shutting_down",
        },
        timed_out=category in {"queue_wait_timeout", "model_inference_timeout"},
        cache_hit=response.headers.get("X-Result-Type") == "cached_answer",
        latency_ms=latency_ms,
        queue_wait_ms=_number(response.headers, "X-Inference-Queue-Wait-Ms"),
        queue_depth=int(_number(response.headers, "X-Inference-Queue-Depth")),
        model=response.headers.get("X-Inference-Model"),
        priority=response.headers.get("X-Inference-Priority"),
    )


async def streaming_request(
    client: httpx.AsyncClient,
    endpoint: str,
    question: str,
) -> LoadResult:
    started = perf_counter()
    queue_wait_ms = 0.0
    queue_depth = 0
    model = None
    priority = None
    cache_hit = False
    error_category = None
    success = False
    try:
        async with client.stream("POST", endpoint, json={"question": question}) as response:
            current_event = None
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    current_event = line[7:]
                    continue
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if current_event == "queue_status":
                    queue_depth = max(queue_depth, int(data.get("queue_position") or 0))
                    priority = data.get("priority")
                elif current_event == "context_ready":
                    cache_hit = bool(data.get("semantic_cache_hit"))
                    model = data.get("model_name")
                    priority = priority or data.get("priority")
                elif current_event == "done":
                    success = True
                    queue_wait_ms = float(data.get("inference_queue_wait_ms") or 0.0)
                elif current_event == "error":
                    error_category = data.get("error_category")
    except httpx.TimeoutException:
        error_category = "model_inference_timeout"
    latency_ms = (perf_counter() - started) * 1000
    return LoadResult(
        success=success,
        rejected=error_category in {
            "queue_full",
            "per_user_queue_limit",
            "service_shutting_down",
        },
        timed_out=error_category in {
            "queue_wait_timeout",
            "model_inference_timeout",
        },
        cache_hit=cache_hit,
        latency_ms=latency_ms,
        queue_wait_ms=queue_wait_ms,
        queue_depth=queue_depth,
        model=model,
        priority=priority,
    )


async def run(args: argparse.Namespace) -> dict[str, object]:
    prompts = tuple(
        item.strip()
        for item in (args.prompts.split("||") if args.prompts else DEFAULT_PROMPTS)
        if item.strip()
    )
    headers = {"Accept": "text/event-stream" if args.streaming else "application/json"}
    if args.bearer_token:
        headers["Authorization"] = f"Bearer {args.bearer_token}"
    endpoint = args.api_root.rstrip("/") + (
        "/knowledge/ask/stream" if args.streaming else "/knowledge/ask"
    )
    timeout = httpx.Timeout(args.timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        request_fn = streaming_request if args.streaming else non_streaming_request

        async def run_user(user_index: int) -> list[LoadResult]:
            return [
                await request_fn(
                    client,
                    endpoint,
                    prompts[(user_index + request_index) % len(prompts)],
                )
                for request_index in range(args.requests_per_user)
            ]

        started = perf_counter()
        grouped = await asyncio.gather(
            *(run_user(index) for index in range(args.users))
        )
        duration = perf_counter() - started
    results = [result for group in grouped for result in group]
    return summarize(results, duration)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-root",
        default=os.getenv("CTV_ONE_LOAD_TEST_API_ROOT", "http://127.0.0.1:8000/api/v1"),
    )
    parser.add_argument(
        "--bearer-token",
        default=os.getenv("CTV_ONE_LOAD_TEST_BEARER_TOKEN", ""),
    )
    parser.add_argument(
        "--users",
        type=int,
        default=int(os.getenv("CTV_ONE_LOAD_TEST_USERS", "10")),
    )
    parser.add_argument(
        "--requests-per-user",
        type=int,
        default=int(os.getenv("CTV_ONE_LOAD_TEST_REQUESTS_PER_USER", "3")),
    )
    parser.add_argument(
        "--streaming",
        action=argparse.BooleanOptionalAction,
        default=os.getenv("CTV_ONE_LOAD_TEST_STREAMING", "false").lower()
        in {"1", "true", "yes", "on"},
    )
    parser.add_argument(
        "--prompts",
        default=os.getenv("CTV_ONE_LOAD_TEST_PROMPTS", ""),
        help="Optional prompts separated by ||.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.getenv("CTV_ONE_LOAD_TEST_TIMEOUT_SECONDS", "300")),
    )
    args = parser.parse_args()
    if args.users < 1 or args.requests_per_user < 1:
        parser.error("users and requests-per-user must both be positive")
    return args


def main() -> int:
    report = asyncio.run(run(parse_args()))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
