# CTV ONE Architecture

[CTV ONE Architecture v1.0](./CTV_ONE_ARCHITECTURE_V1.md) is the canonical baseline. Supporting implementation notes are [search runtime](./004-search-runtime-pipeline.md), [local providers](./005-local-provider-boundaries.md), [infrastructure providers](./006-infrastructure-provider-boundaries.md), [context](./007-enterprise-context-engine.md), [graph](./008-enterprise-relationship-graph.md), and [graph runtime](./009-graph-runtime-integration.md).

Mermaid sources are in [diagrams](./diagrams/). Status terminology in the v1.0 specification is authoritative.

[Organizational Memory Contracts](./010-organizational-memory.md) documents the Phase 4.4A contract-only extension point.

[Memory Runtime Foundation](./011-memory-runtime.md) documents the Phase 4.4B in-process, non-persistent runtime.

[Enterprise Temporal Evidence](./012-enterprise-temporal-evidence.md) documents the Phase 4.5 evidence pipeline that enables eligible source timestamps to produce observations.

[Temporal Evidence Provider Expansion](./013-temporal-evidence-provider-expansion.md) records the Phase 4.5B provider audit and active coverage.

[AI Context Package Contracts](./014-ai-context-package-contracts.md) documents the Phase 4.6 bounded, model-independent AI handoff.

[AI Model Orchestrator Contracts](./015-ai-model-orchestrator-contracts.md) documents the Phase 4.7A deterministic execution-planning boundary. Runtime execution and model adapters remain planned.

[AI Model Runtime Foundation](./016-ai-model-runtime-foundation.md) documents Phase 4.7B adapter-bound execution lifecycle. Production model adapters remain planned.

[Ollama Model Adapter](./017-ollama-model-adapter.md) documents Phase 4.7C.1 isolated Ollama transport and normalization. Production runtime cutover remains unimplemented.
