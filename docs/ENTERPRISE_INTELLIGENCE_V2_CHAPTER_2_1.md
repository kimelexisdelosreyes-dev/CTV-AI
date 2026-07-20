# V2.0-C2.1 Agent Runtime Release Validation

## Composer and reasoning diagnosis

The original 60-second execution-engine timeout enclosed queue submission, queue waiting, lease ownership, and model execution. The model helper also opened a separate 60-second timeout after acquiring the lease. Live queue wait was zero, so the observed failures came from inference rather than admission, but the overlapping scopes obscured the origin.

The original reasoning request contained 10,143 prompt characters and the composer request contained 12,227. Both user payloads reached their hard slice. The composer slice produced invalid JSON and included duplicate knowledge facts/evidence, duplicate operations snapshot text, and task/version/duration/resource metadata that composition did not need.

C2.1 retains the 180-second total supervisor ceiling and the 60-second default retrieval-task ceiling. Reasoning has a 90-second upper bound and composition has a 120-second upper bound. Queue wait uses its own budget; inference uses the role-specific ceiling bounded by the remaining task deadline; the outer task deadline remains the final guard. Categories distinguish queue timeout, inference timeout, total task deadline, dependency failure, and invalid result.

## Bounded composition and strategies

Composition input is valid structured JSON capped by total characters, per-result characters, and evidence count. It orders factual retrieval output before recommendations, deduplicates evidence IDs and warnings, retains citation labels and bounded excerpts, and excludes lifecycle/resource metadata.

`composition_strategy` is one of:

- `llm` for successful comparison, recommendation, analysis, risk, tradeoff, or executive narrative.
- `deterministic` for concise retrieval-only/status composition.
- `fallback_deterministic` when an optional reasoning/dependency result is unavailable or model composition fails.

The deterministic formatter exposes findings, sources, recommendations when present, warnings, and unavailable sections without hidden reasoning.

## Cache latency

The persistent semantic cache remains authoritative. A bounded process-local hot exact layer stores already validated results by the full exact key, which includes source fingerprints and policy/model state. Repeated hot hits perform no cache database query or hit-counter write. Store and invalidation operations evict relevant hot state, and expiry is enforced before return.

Instrumentation separates authentication, request validation, cache key/state construction, persistent query, hot lookup, deserialization, persistence, response-model construction, endpoint handling, and the response-serialization/middleware estimate. Cache hits continue to bypass supervisor planning, Agent Runtime resolution/readiness checks, inference queue admission, and Ollama.

Persisted hit statistics no longer write synchronously for every hot hit; runtime statistics add the process-local hot-hit count. A process restart clears hot entries and the first eligible request may still require persistent exact or embedding-backed semantic lookup.

## Configuration

```text
CTV_ONE_AGENT_REASONING_TIMEOUT_SECONDS=90
CTV_ONE_AGENT_COMPOSER_TIMEOUT_SECONDS=120
CTV_ONE_AGENT_COMPOSITION_MAX_EVIDENCE_ITEMS=8
CTV_ONE_AGENT_COMPOSITION_MAX_CHARS_PER_RESULT=2500
CTV_ONE_AGENT_COMPOSITION_MAX_TOTAL_CHARS=8000
CTV_ONE_SEMANTIC_CACHE_HOT_EXACT_MAX_ENTRIES=128
```

These are role-specific ceilings and do not weaken budgets or change the global supervisor deadline. The live `backend/.env` remains user-owned and unchanged.
