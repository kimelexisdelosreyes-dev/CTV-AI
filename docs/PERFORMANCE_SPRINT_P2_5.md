# P2.5 Context-Aware Semantic Cache

## Purpose and architecture

The Company Brain cache avoids Ollama for eligible repeated stable knowledge and operations questions. PostgreSQL is authoritative for answers, metadata, expiry, scope, and embeddings. This keeps cache correctness independent of Qdrant and does not require pgvector. Exact lookup is a deterministic indexed query. Semantic lookup embeds the normalized question, loads a small set of candidates already filtered by scope and context-state fingerprint, and applies a conservative cosine threshold in process.

Lookup occurs after deterministic intelligence routing and before context retrieval. On a miss, the existing parallel retrieval, prompt budgeting, model routing, and Ollama paths remain unchanged. Writes happen only after a complete successful answer is available. Cache read/write failures fail open.

## Exact and semantic hits

Exact keys include the normalized question, scope, and invalidation fingerprint. Normalization folds case and removes punctuation and repeated whitespace. Semantic candidates must have the same scope, route, context types, source-state fingerprint, assistant/prompt policy, router policy, and configured model policy. Similarity alone never produces a hit. The default threshold is `0.94`, and only five candidates are compared.

## Eligibility and isolation

| Request | Default | Scope |
| --- | --- | --- |
| Stable policy/manual/SOP/brand lookup | Eligible | `global_company` |
| Snapshot-backed operations summary | Eligible | `global_company` with snapshot fingerprint |
| Mixed stable knowledge and operations | Eligible | `global_company` with both fingerprints |
| Employee-context answer | Ineligible in P2.5 | Deterministic user scope is reserved |
| Conversation/history-dependent answer | Ineligible in P2.5 | Deterministic conversation scope is reserved |
| Creative, rewriting, formatting, or complex reasoning | Ineligible | None |
| Explicit refresh/latest/recalculate/bypass request | Ineligible | None |
| Degraded, failed, empty, malformed, truncated, oversized response | Never stored | None |

Employee and conversation requests receive distinct scope keys before being skipped, so future opt-in support cannot cross users or conversations. P2.5 deliberately prefers false misses.

## Invalidation and expiry

The context-state fingerprint includes the route and context types, latest successful operations snapshot identity/timestamp, ready-document count/latest update/chunk count, prompt policy version, router policy version, assistant/category, and configured role models. A new successful Monday snapshot therefore misses all earlier operations entries. Knowledge ingestion, deletion, replacement, or status/revision changes change the global knowledge fingerprint. Operations entries default to 15 minutes; other entries default to 24 hours. Expired rows miss and can be purged safely.

## Streaming and non-streaming behavior

`POST /knowledge/ask` returns the existing response model and persists the assistant message normally. `POST /knowledge/ask/stream` preserves `start`, `context_ready`, `token`, and `done`; `context_ready` adds safe cache flags, and cached text uses the normal token event. The frontend needs no alternate renderer. In both modes, a hit records `ollama_skipped_due_to_cache=true` and does not invoke Ollama.

## Configuration

All settings use the `CTV_ONE_SEMANTIC_CACHE_` prefix. See `backend/.env.example`. Important controls are enabled/exact/similarity flags, similarity threshold, default and operations TTLs, maximum answer characters, maximum candidates, and explicit prompt/router policy versions. Bump a policy version whenever answer-affecting prompt or routing behavior changes.

## Privacy and security boundaries

Rows contain normalized questions, safe visible answers, citation identifiers, safe personalization metadata, model/route metadata, version fingerprints, and optional question embeddings. They never contain the assembled hidden prompt, retrieved chunk text, employee context, conversation history, credentials, or tokens. Aggregate statistics expose counts only, not answers.

## Benchmark process

Run the baseline normally for cache-miss regression. Set `CTV_ONE_BENCHMARK_CACHE_PASSES=true` to run three labeled passes: `cold_cache`, `exact_hit`, and `semantic_hit` (conservative paraphrases). JSON, CSV, and Markdown reports include eligibility, hit type, score, lookup duration, scope, write duration, Ollama-skipped state, inference duration, and total duration.

## Management and limitations

The service exposes internal functions to invalidate knowledge, operations, or user scope; purge expired rows; and return safe aggregate statistics. No public clear endpoint is added in this sprint. Cache entries are local to the configured PostgreSQL database; cross-server synchronization, Redis, pgvector indexing, automatic threshold tuning, LLM verification, employee/history caching, creative caching, and partial-response caching remain deferred.

Apply migration `0010` before enabling the cache in a deployed environment. Disabling the cache preserves existing inference behavior.
