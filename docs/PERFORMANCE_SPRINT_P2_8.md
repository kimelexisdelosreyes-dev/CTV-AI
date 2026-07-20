# Performance Sprint P2.8: Inference Admission and Concurrency Safety

## Architecture and insertion point

CTV ONE now uses a process-local, asyncio-native inference scheduler for Company Brain and its developer benchmark. The scheduler stores identifiers, model metadata, priority, timestamps, and cost class only. It never stores prompts, answers, tokens, employee names, or conversation text.

The request order is:

1. Authentication and request validation.
2. Deterministic intent and context routing.
3. Semantic-cache lookup.
4. Immediate cache-hit or evidence-fallback response, when applicable.
5. Context retrieval and prompt assembly.
6. Model routing.
7. End any read-only SQLAlchemy transaction opened during retrieval.
8. Queue admission and model-slot acquisition.
9. Ollama inference inside a cancellation-safe lease.
10. Lease release, cache write, response formatting, and conversation persistence.

Admission is deliberately immediately before Ollama. Cache lookup, Qdrant search, Monday snapshot reads, employee context, history retrieval, and prompt construction do not consume an inference slot.

## Limits and configuration

The tracked defaults target one local GPU:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `CTV_ONE_INFERENCE_QUEUE_ENABLED` | `true` | Enable bounded admission. Disabled mode is immediate/pass-through. |
| `CTV_ONE_INFERENCE_GLOBAL_CONCURRENCY` | `2` | Maximum active Company Brain/benchmark inference calls. |
| `CTV_ONE_INFERENCE_GLOBAL_QUEUE_SIZE` | `20` | Maximum waiting requests; active requests are separate. |
| `CTV_ONE_INFERENCE_DEFAULT_TIMEOUT_SECONDS` | `180` | Maximum inference lease execution time. |
| `CTV_ONE_INFERENCE_QUEUE_WAIT_TIMEOUT_SECONDS` | `120` | Maximum admission wait. |
| `CTV_ONE_INFERENCE_MODEL_QWEN3_8B_CONCURRENCY` | `2` | qwen3:8b/model-role-family limit. |
| `CTV_ONE_INFERENCE_MODEL_DEEPSEEK_R1_14B_CONCURRENCY` | `1` | DeepSeek/reasoning limit. |
| `CTV_ONE_INFERENCE_PER_USER_ACTIVE_LIMIT` | `1` | Active leases per authenticated user. |
| `CTV_ONE_INFERENCE_PER_USER_QUEUE_LIMIT` | `3` | Waiting requests per authenticated user. |
| `CTV_ONE_INFERENCE_SHUTDOWN_GRACE_SECONDS` | `30` | Grace period for active inference. |
| `CTV_ONE_INFERENCE_PRIORITY_AGING_SECONDS` | `30` | Wait interval before one priority-level promotion. |

Model environment fragments normalize uppercase with every non-alphanumeric run replaced by `_`; for example, `deepseek-r1:14b` becomes `DEEPSEEK_R1_14B`. P2.8 exposes explicit settings for the two deployed model families. Additional model-specific variables should follow the same normalization rule and be added to `InferenceQueueConfig.from_settings()`.

## Priority and fairness

Priority is deterministic and never invokes an LLM or uses prompt length:

1. `interactive_fast`: fast, knowledge, and operations model roles.
2. `interactive_standard`: balanced, default, and other interactive roles.
3. `interactive_reasoning`: explicit reasoning-role work.
4. `background`: benchmarks and warmups.

FIFO is preserved for each user within a priority. Scheduling rotates among eligible users at the best effective priority. A user may not exceed the configured active or waiting limits. Waiting work ages toward the highest priority, preventing permanent background starvation. The DeepSeek limit of one prevents simultaneous reasoning jobs, while a global limit of two leaves capacity for an eligible qwen request.

## Streaming behavior

Streaming retains the existing `start`, `context_ready`, `token`, `done`, and safe `error` events. If a request must wait, it receives one optional `queue_status` event containing only approximate position, estimated wait, priority, and model role. No fake token is emitted.

`context_ready` is emitted after admission for cache misses. Cache hits keep the established protocol without entering the queue. While queued, disconnect checks run at short intervals. A disconnected waiter is removed before it can acquire a slot. Active streams release their global and model leases on success, error, timeout, generator cancellation, or disconnect.

## Non-streaming behavior and overload

Successful responses retain the existing JSON schema. Safe response headers expose queue wait, priority, queue depth at entry, and selected model when available.

Queue capacity and per-user queue rejection use HTTP 429. Queue-wait expiry and draining use HTTP 503. `Retry-After` is included when practical. Safe categories are `queue_full`, `per_user_queue_limit`, `queue_wait_timeout`, `request_cancelled`, and `service_shutting_down`; internal queue entries are never returned.

## Cancellation, timeout, and shutdown

Every acquired lease is released in `finally`. The configured inference timeout wraps Ollama calls in addition to the HTTP-client timeout. Queued cancellation removes the entry immediately. During shutdown the service stops accepting work, rejects all pending work, waits for active requests for the grace period, then cancels remaining owner tasks. The queue does not persist work across process restarts.

## Cache interaction

Semantic-cache hits return before admission, retain `ollama_skipped_due_to_cache`, and increment `cache_bypass_count`. Evidence fallbacks also avoid Ollama and therefore do not need an inference slot. Cache writes occur after lease release.

## Diagnostics and metrics

Administrators can call `GET /api/v1/runtime/inference/status`. It reports aggregate limits, active and queued counts, priority/model distributions, oldest and average wait, rejection/timeout/cancellation counts, completions, and cache bypasses. Employees receive HTTP 403. No raw or hashed user identifier is currently exposed.

Performance instrumentation includes:

- `inference_queue_enabled`, `inference_queue_admitted`, `inference_queue_bypassed`
- `inference_queue_rejected`, `inference_queue_rejection_reason`
- `inference_queue_priority`, `inference_queue_position`, `inference_queue_wait_ms`
- `inference_queue_depth_at_entry`, `inference_active_global`
- `inference_active_for_model`, `inference_model_limit`, `inference_user_active_count`
- `inference_cancelled`, `inference_timed_out`, `inference_lease_duration_ms`

Developer benchmark result rows include enabled, priority, wait, and entry-depth fields, and benchmark work is explicitly `background` priority.

## Local load test

Start an authenticated API, set a token in the shell (never in source), then run:

```powershell
$env:CTV_ONE_LOAD_TEST_API_ROOT='http://127.0.0.1:8000/api/v1'
$env:CTV_ONE_LOAD_TEST_BEARER_TOKEN='<token>'
$env:CTV_ONE_LOAD_TEST_USERS='10'
$env:CTV_ONE_LOAD_TEST_REQUESTS_PER_USER='3'
$env:CTV_ONE_LOAD_TEST_STREAMING='false'
backend\.venv\Scripts\python.exe scripts\company_brain_load_test.py
```

Set `CTV_ONE_LOAD_TEST_PROMPTS` to prompts separated by `||` for an optional mix. The JSON report contains request outcomes, cache hits, mean/median/p95 latency, queue wait/depth, throughput, models, and priorities. It never prints the token or prompts.

## Production recommendations and limitations

Keep the supplied limits for the current qwen3:8b plus DeepSeek single-GPU deployment. Validate 10- and 20-user loads before increasing concurrency; higher concurrency can increase GPU memory pressure and worsen total latency.

This queue is intentionally process-local. Multiple API worker processes each have independent limits and counters, so deploy one inference-serving worker until a later distributed scheduler exists. It provides no preemption, GPU-memory admission, token-cost estimation, quotas, or cross-node cancellation. Legacy non-Company-Brain chat compatibility endpoints are not migrated in this sprint; their consolidation behind the same admission service is the next safety extension if they are exposed to simultaneous production traffic.
