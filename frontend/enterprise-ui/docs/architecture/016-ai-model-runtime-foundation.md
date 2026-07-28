# AI Model Runtime Foundation

Phase 4.7B introduces the execution boundary beneath an immutable `AIExecutionPlan`. The planner remains responsible for eligibility, scoring, and the exact fallback sequence; the runtime validates that plan, resolves an adapter deterministically, executes only its primary and planned fallbacks, and returns a frozen, serializable result.

The adapter registry keeps executable adapters private. Its public snapshot contains descriptors only and is ordered by adapter ID. Resolution uses selected model identity, provider type, location, execution mode, enabled status, configured priority, then lexical adapter ID. There is no provider SDK in the runtime core.

Runtime policy and limits can only tighten plan policy and limits. Retries default to disabled. Cancellation is checked before each attempt and forwarded as an adapter signal. A total per-attempt timeout races execution, aborts its signal, and produces a controlled timeout result. Attempts are sequential and immutable; no new models are selected or added.

Adapter output is normalized to text/structured data/references/citations plus safe usage metadata. Raw errors are converted to controlled categories; public results retain no stack traces, executable objects, signals, credentials, SDK responses, or provider transport data. Safe telemetry is intentionally deferred; no telemetry sink is wired in this foundation.

`DeterministicTestAdapter` validates the boundary without calling a model. Production Ollama and cloud adapters remain **PLANNED**; this foundation is not connected to application inference.

Phase 4.7C.1 supplies an isolated Ollama adapter beneath this foundation. The runtime itself remains provider-independent and no production cutover is performed.
