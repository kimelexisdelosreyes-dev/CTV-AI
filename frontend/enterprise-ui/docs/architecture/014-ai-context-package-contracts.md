# AI Context Package Contracts

Phase 4.6 defines `AIContextPackage`: a provider-, model-, and prompt-independent immutable handoff for future AI orchestration. The builder accepts normalized search results plus existing Context, Graph Runtime, and optional Memory Runtime outputs. It does not query providers, rebuild state, call models, construct prompts, persist data, or add UI.

The package uses deterministic source references (`context-{createdAt}`, graph session ID, memory session ID), verifies graph/context and memory/graph compatibility, and returns controlled `ready`, `ready-partial`, `ready-empty`, `stale`, or `cancelled` results. Context and graph are required; absent or ready-empty Memory is explicit rather than fabricated.

All sections are bounded and deeply frozen. Search metadata is restricted to normalized safe fields, excluding location/path, transcript, and excerpt fields. Evidence is deduplicated by deterministic evidence ID and retains only provider/entity references, timestamp semantics, precision, confidence, and controlled references. Diagnostics are bounded, serializable, deterministic, and non-sensitive.

Default policy permits future reasoning, summarization, and generation while requiring citations, evidence traceability, and uncertainty disclosure. Provider access, tools, external knowledge, recommendations, sensitive data, and Memory mutation are disabled. These are package declarations only; no policy is executed against an AI system in this phase.

The package builder is callable at the service boundary but is not wired to the active search runtime, so this phase is **PARTIALLY IMPLEMENTED**. That is intentional: a later AI orchestration phase must decide when to request a package and how to adapt it for a model without changing this canonical enterprise contract.
