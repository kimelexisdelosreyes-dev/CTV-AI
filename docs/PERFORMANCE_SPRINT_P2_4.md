# Performance Sprint P2.4: Intelligent Model Router

## Purpose

Company Brain uses a deterministic router to select a configured Ollama model
after context retrieval and prompt budgeting. Routing does not make an extra LLM
call and does not change prompt content. When role models are not configured, the
existing `OLLAMA_MODEL` behavior remains available as the final fallback.

## Configuration

- `CTV_ONE_MODEL_ROUTER_ENABLED`: enables role-based routing.
- `CTV_ONE_MODEL_FAST`: short employee and simple requests.
- `CTV_ONE_MODEL_BALANCED`: mixed operations and knowledge requests.
- `CTV_ONE_MODEL_REASONING`: complex analysis and planning requests.
- `CTV_ONE_MODEL_OPERATIONS`: operations-only requests.
- `CTV_ONE_MODEL_KNOWLEDGE`: knowledge-only requests.
- `CTV_ONE_MODEL_DEFAULT`: router fallback; defaults to `OLLAMA_MODEL` when unset.
- `CTV_ONE_MODEL_AVAILABILITY_TTL_SECONDS`: installed-model cache lifetime.

The example local mapping uses `qwen3:8b` for fast, operations, and knowledge;
`qwen3:14b` for balanced; and `deepseek-r1:14b` for reasoning. These names are
configuration, not requirements. Installations may use any compatible Ollama
models.

Model size alone does not guarantee lower latency. If an 8B model spills heavily
to CPU or has unstable generation throughput, map the affected role (notably
operations) to the balanced model and confirm the choice with repeated benchmarks.

## Routing Matrix

| Request | Model role |
| --- | --- |
| Simple knowledge lookup | knowledge |
| Simple operations status | operations |
| Employee-only context | fast |
| Mixed operations and knowledge | balanced |
| Complex analysis, strategy, risk, forecast, or tradeoffs | reasoning |
| Unknown route | fallback |

Complexity is classified from existing request metadata: analysis keywords,
context combination, source count, final prompt characters, and estimated prompt
tokens. The rules are fixed and explainable; benchmark labels are not inputs.

## Availability And Fallbacks

Configured role models are checked against Ollama's installed-model list. The
result is cached and is not requested on every ask. An unavailable role model
falls back to `CTV_ONE_MODEL_DEFAULT`, then to `OLLAMA_MODEL` when that model is
known to be installed. Failure to list models does not fail the request.

Unconfigured roles use the configured default. Explicit developer model
overrides remain authoritative. Setting `CTV_ONE_MODEL_ROUTER_ENABLED=false`
restores the existing `OLLAMA_MODEL` selection without an availability request.

## Instrumentation And Benchmarking

Performance events and benchmark reports include only the selected model, role,
complexity, reason, fallback state, availability-check state, and routing time.
They do not contain prompts, retrieved chunks, task content, employee context, or
credentials.

Run the same ten-case baseline before and after enabling role mappings. Compare
`model_selected`, `model_role`, `model_routing_complexity`, inference duration,
and total duration. Model loading and GPU memory pressure can affect the first
request after switching models, so repeated cases should be compared separately.

## Limitations

The router uses heuristics rather than learned quality scores. It does not manage
GPU queues, warm models, semantic caching, ensembles, permissions, or automatic
benchmark tuning. Availability confirms installation, not current memory capacity
or generation quality.
