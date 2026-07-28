# Chapter 3 Sprint 3.3 — Provider Snapshot Orchestration

Atlas provider orchestration is an explicit pre-compilation layer. Callers supply an immutable execution request containing a canonical provider plan, fixed compilation timestamp, compiler policy, failure policy, and safe metadata. There is no implicit “all providers” mode or dynamic provider discovery.

`AtlasProviderOrchestrator` resolves only listed providers from the static registry, verifies lifecycle, capability, and contract compatibility, then invokes `collect()` with a narrow request and collection context. Four asynchronous slots bound provider concurrency and each plan supplies a bounded timeout. Required failures stop before compilation; optional failures and timeouts become sanitized operational statuses and deterministic selection exclusions.

Provider output is validated into `AtlasValidatedProviderResult`, with immutable records, relations, metadata, warnings, classification, and deterministic fingerprint. Records and relation candidates are canonically ordered before conversion to `AtlasProviderInputSnapshot`. Caller time is preserved; provider duration, completion order, counters, and runtime state never enter the snapshot fingerprint.

The runtime owns one orchestrator and exposes `execute_provider_plan()` only as an internal service method. The orchestrator constructs the immutable snapshot and invokes the existing `compile_context()` entrypoint. Compiler and runtime compilation remain provider-blind. No public endpoint, persistence, Forge/Nexus integration, database access, inference, or production request-path use is introduced.

Operational orchestration metrics are bounded thread-safe scalars: attempts, results, active/peak work, provider status counts, sanitized errors, duration, counts, snapshot bytes, and compilation success. Diagnostics expose availability, concurrency, and these aggregates without provider configuration or content.

Focused tests cover contracts, registry resolution, successful/partial/failing/malformed/timeout behavior, canonical snapshot construction, 100 repeats, 50 completion-order permutations, 50 record-order permutations, 20 concurrent requests, mixed failures, metrics, diagnostics, isolation, and lifecycle gating.

Offline benchmark results (five runs): the three-provider/51-record fixture measured 28.404 ms median total, 26.232 ms compilation, and 2.172 ms orchestration overhead. The six-provider/504-record fixture measured 239.063 ms median total, 220.798 ms compilation, and 18.266 ms orchestration overhead. Moderate artifacts were 43,225 snapshot bytes, 11,804 package bytes, and 509,583 manifest bytes.
