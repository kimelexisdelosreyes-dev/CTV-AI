# Enterprise Intelligence V2 Chapter 4.1

## Shadow Architecture

Atlas Shadow Mode runs the approved Atlas provider orchestrator, runtime compiler,
Forge adapter, prompt comparison, trace generation, metrics, and bounded in-memory
trace buffering alongside the production chat request path.

Shadow Mode never sends Atlas context to the LLM. The production prompt remains
the only prompt used for inference.

## Atlas Trace

`AtlasTrace` is immutable and canonically serializable. It stores fingerprints,
safe summaries, counts, feature flag state, prompt-size comparisons, and
operational timings. It does not store prompt text, provider payloads, AIR,
graphs, manifest decisions, user messages, or chain-of-thought.

## Comparison Pipeline

The pipeline renders the production prompt representation and a shadow prompt
with Atlas context inserted through the existing Forge prompt builder. Only
bytes, estimated tokens, section counts, and Atlas addition counts are retained.

## Feature Flags

`ctv_one_atlas_shadow_enabled` defaults to `false` and enables compilation,
Forge adaptation, tracing, comparison, and metrics without prompt injection.

`ctv_one_atlas_canary_enabled` defaults to `false` and is reserved.

`ctv_one_atlas_live_enabled` defaults to `false` and is reserved.

Shadow Mode does not imply Canary or Live mode.

## Ring Buffer

Traces are not persisted. The optional in-memory ring buffer stores at most 100
traces and evicts the oldest trace first.

## Diagnostics

Atlas runtime diagnostics include aggregate Shadow Mode diagnostics:
shadow enabled, shadow requests, shadow compilations, shadow failures, shadow
traces, average shadow latency, average package bytes, and average Forge bytes.
Diagnostics never include prompt text, node content, or provider content.

## Benchmarks

`backend/scripts/benchmark_shadow_mode.py` measures provider orchestration,
compiler, adapter, trace, comparison, and total shadow latency. Results are
observational and do not gate production behavior.

## Limitations

Canary and Live flags are intentionally reserved. The current approved provider
registry is empty, so Shadow Mode validates the orchestration and compiler path
with an empty provider plan until future providers are explicitly approved.
