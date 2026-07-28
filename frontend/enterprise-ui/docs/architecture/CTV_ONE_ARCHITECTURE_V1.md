# CTV ONE Architecture v1.0

## 1. Executive Summary

CTV ONE is an Enterprise Intelligence Platform: a shared intelligence layer over enterprise sources, not a single chatbot, provider-specific search UI, graph database frontend, or replacement for source systems. Its progression is **Enterprise Data -> Search -> Runtime Context -> Relationships -> future Memory -> future AI**.

Status vocabulary: **IMPLEMENTED** means code participates in runtime; **IMPLEMENTED - NOT YET RUNTIME-INTEGRATED** means validated code is not on the main path; **PARTIALLY IMPLEMENTED** means a bounded portion exists; **PLANNED** means approved future architecture; **EXTENSION POINT** is a designed future boundary; **PROHIBITED DEPENDENCY** must not be introduced; **OUT OF SCOPE** is intentionally excluded from v1.0.

| Subsystem | Status | Runtime integrated | Persistence | Next work |
| --- | --- | --- | --- | --- |
| Universal Search / SearchService / registry | IMPLEMENTED | Yes | No | Provider maturity |
| Provider SDK and local providers | IMPLEMENTED | Yes | No | Live connectors |
| Infrastructure metadata providers | IMPLEMENTED | Yes | No | Indexed connector sources |
| ContextEngine / EntityResolver / ContextSnapshot | IMPLEMENTED | Yes | No | Context inputs |
| GraphBuilder / RelationshipGraph / QueryEngine | IMPLEMENTED | Yes, through graph runtime | No | Stable identities |
| GraphRuntimeService | IMPLEMENTED | Yes; graph-primary relationship presentation retains normalized fallback | No | Stable relationship identity |
| Organizational Memory | PARTIALLY IMPLEMENTED | Runtime session is invoked after graph; local-file temporal evidence can produce observations; no persistent retention | No | Retention governance |
| Enterprise Temporal Evidence | IMPLEMENTED | Local-file, knowledge, and project source metadata propagates through Context, graph provenance, and Memory | No | Live-provider timestamp contracts |
| AI Orchestrator | PLANNED | No | No | Future phase |
| Live connectors | PLANNED | No | No | Phase 5 |

## 2. Principles

1. **Provider neutrality:** [SearchService](../../src/services/search/SearchService.ts) discovers registered contracts rather than importing source implementations.
2. **UI independence:** contracts and services do not import React, JSX, or CSS.
3. **Deterministic processing before AI:** search ranking, context confidence, and graph traversal are explicit algorithms.
4. **Explicit context:** unknown context remains absent; [ContextEngine](../../src/services/context/ContextEngine.ts) does not infer missing enterprise facts.
5. **Immutable snapshots:** ContextSnapshot and GraphSnapshot are frozen at service boundaries.
6. **Canonical identity and provenance:** entity IDs and provider/source attribution survive merges.
7. **Bounded traversal:** graph queries default to depth 1 and cap at depth 3.
8. **Partial failure tolerance:** provider and graph failures do not invalidate usable search results.
9. **Local-first, cloud-extensible:** current providers adapt local-demo records; connectors are extension points.
10. **Explainability before automation:** diagnostics, evidence, and explicit metadata precede automation.

Security, authorization, and source permissions are separate future responsibilities. Neither graph topology nor context confidence authorizes access.

## 3. System and Layers

Current source categories are local enterprise datasets, indexed files, knowledge, projects, infrastructure, storage, workstations, and compute metadata. NAS, Google Drive, Alibaba OSS, Monday.com, PostgreSQL, Qdrant, model gateways, and monitoring are PLANNED.

| Layer | Actual modules | Owns | Must not depend on |
| --- | --- | --- | --- |
| Presentation | `src/components`, `src/design-system`, `src/features/search` | interaction and temporary display state | providers, graph internals |
| Application coordination | `search-service-adapter.ts`, composition roots | handoffs between snapshots and services | source adapters |
| Intelligence | `services/context`, `services/graph` | relevance, identity, topology, bounded queries | UI, provider execution |
| Enterprise service | `services/search`, cache, telemetry | search execution, ranking, diagnostics | concrete providers |
| Provider integration | `services/providers/sdk`, registry | lifecycle, health, normalization | React, graph services |
| Source adapters | `services/providers/local` | local-demo extraction | presentation types |

Allowed direction: Presentation -> adapter -> coordinator -> service -> registry -> provider -> source adapter -> data. Context flows Runtime Input -> ContextEngine -> ContextSnapshot. Graph flows ContextSnapshot -> ContextGraphAdapter -> GraphBuilder -> GraphSnapshot -> GraphQueryEngine -> presentation adapter.

**PROHIBITED DEPENDENCY:** providers importing React, presentation, graph services, or ContextEngine; SearchService importing provider implementations or RelationshipGraph; graph services executing providers/SearchService; ContextEngine importing GraphRuntimeService; components building registries or graph state per render.

## 4. Search and Provider Platform

The [SearchService](../../src/services/search/SearchService.ts) validates input, discovers providers, executes them in parallel, applies timeout/cancellation, isolates failures, deduplicates stable keys, ranks deterministically, caches results, and returns diagnostics. Graph-based ranking is not enabled. Universal Search must remain usable if context or graph work fails.

[BaseProvider](../../src/services/providers/sdk/BaseProvider.ts) standardizes initialize, validate, execute, normalize, diagnostics, cleanup, timeout, retry, cancellation, and health. Current providers are DemoSearchProvider; local files, knowledge, projects; and metadata-only infrastructure, storage, workstation, and compute providers. They are `local-demo`, not live integrations.

Infrastructure providers do not monitor, ping, scan, crawl, execute commands, connect NAS, or poll Docker/Ollama/GPU systems.

## 5. Context and Graph

[ContextEngine](../../src/services/context/ContextEngine.ts) answers “what is relevant now?” from explicit module, page, project, asset, selected entity, recent-search, provider, and relationship contributions. [EntityResolver](../../src/services/context/EntityResolver.ts) merges equivalent explicit IDs while preserving attribution. Context is not memory, persistence, provider execution, AI reasoning, authorization, or graph traversal.

The [RelationshipGraph](../../src/services/graph/RelationshipGraph.ts) is deterministic and in memory. [GraphBuilder](../../src/services/graph/GraphBuilder.ts) ingests context-shaped entities and direct relationships. [GraphQueryEngine](../../src/services/graph/GraphQueryEngine.ts) performs stable BFS, path lookup, cycle-safe traversal, entity/relationship filtering, AbortSignal checks, and output bounds. Presentation labels without stable targets are retained as unresolved references; they do not create fabricated nodes.

Graph identity uses `ResolvedEntity.id`, source IDs, provider IDs, and aliases. Display titles alone never merge nodes. Colon-qualified IDs are marked provisional. Graph confidence is evidence quality, not truth probability.

## 6. Runtime Lifecycle and Ownership

Current runtime search path is:

`Universal Search -> Search presentation adapter -> SearchService -> registry -> providers -> normalized results -> ContextEngine -> ContextSnapshot -> GraphRuntimeService -> GraphSnapshot -> existing presentation fallback`

[GraphRuntimeService](../../src/services/graph/runtime/GraphRuntimeService.ts) exists and is invoked by the search adapter. It owns one application-scoped session, versioning, same-snapshot reuse, invalidation, reset, cancellation checks, immutable sessions, and bounded query access. It is **IMPLEMENTED**: selected search results resolve through stable graph identity candidates and graph-resolved rows are primary when available; normalized relationships remain the display fallback.

SearchService owns aggregation/ranking; ProviderRegistry owns provider discovery/order; providers own source execution/health; ContextEngine owns ContextSnapshot; EntityResolver owns context identity merges; RelationshipGraph owns topology; GraphQueryEngine owns bounded queries; presentation owns interaction/selection only. No UI component owns canonical enterprise data.

## 7. Failure, Diagnostics, Cache, and Safety

One provider failure leaves other results available. Context or graph failure leaves search usable. Graph lookup failure preserves normalized relationship fallback. Telemetry is optional and must use counts, durations, statuses, provider IDs, and diagnostics, never file contents, transcripts, raw document content, prompts, or full graph payloads.

Search cache is IMPLEMENTED. Provider cache abstractions are IMPLEMENTED but provider-specific runtime wiring remains incomplete. Graph runtime retains/reuses the current session but has no persistence.

Snapshots are immutable for deterministic concurrency, stale-result protection, reproducible diagnostics, and future auditability. They are not durable records.

## 8. Extension Model and Future Architecture

New sources follow: source adapter -> SDK provider -> manifest -> registry -> normalized result -> context contribution -> graph contribution. Providers must not own global ranking, traversal, memory, prompts, or rendering.

**PLANNED Organizational Memory:** durable evidence-backed enterprise events and immutable MemorySnapshots, not chat history, surveillance, graph ownership, authorization, or LLM-generated facts. Phase 4.4A defines [contract-only memory vocabulary](./010-organizational-memory.md); the current runtime is in-process only and has no persistence.

**PLANNED AI Orchestrator:** consumes access-filtered search/context/graph/memory evidence for routing and task execution. AI is the final consumer, not the center of the architecture.

## 9. Repository Map

- `src/contracts/search`, `src/contracts/context`, `src/contracts/graph`
- `src/domain/infrastructure`, `src/domain/context`, `src/domain/graph`
- `src/services/search`, `src/services/context`, `src/services/graph`
- `src/services/providers/sdk`, `src/services/providers/local`
- `src/features/search/search-service-adapter.ts`
- `src/services/search/createSearchService.ts`, `src/services/graph/createGraphRuntimeService.ts`
- `docs/architecture`, `scripts/test-*.mjs`

## 10. Compliance Checklist

- Does a new service import UI, React, JSX, CSS, or component props?
- Does a provider depend on ContextEngine or graph services?
- Does SearchService import concrete providers or graph implementation?
- Are missing values fabricated, identities title-only, or attribution lost?
- Are snapshots immutable and traversal bounded?
- Does one failure break the pipeline?
- Does an external connector use source adapter -> provider SDK?
- Is sensitive content logged or does AI bypass deterministic services?
- Are authorization boundaries respected and planned work labeled correctly?
- Were dependency tests, architecture docs, lint, typecheck, tests, build, and diff checks updated?

## 11. Current Limitations and Roadmap

- Graph runtime construction and graph-primary relationship presentation are implemented, but many provider relationship targets remain label-only and unresolved.
- Direct TypeScript runtime test tooling is not configured; the Node harness validates contracts and architecture behavior.
- Many relationships use presentation labels rather than stable target IDs and remain unresolved.
- Context and graph are not persisted; graph ranking is disabled.
- Organizational Memory is an in-process, evidence-first runtime with limited local-file temporal coverage; AI orchestration, live connectors, authorization enforcement, and monitoring are not implemented.
- Infrastructure health is indexed metadata only; provider-specific cache/telemetry wiring remains incomplete.

Completed: Phases 4.1, 4.1A-D, 4.2, 4.3 foundation, 4.3A graph runtime integration, 4.4A-B memory foundation, 4.5 temporal evidence, and 4.5B provider expansion. Phase 4.6 AI Context Package Contracts is **PARTIALLY IMPLEMENTED**: contracts and callable builder exist, but the runtime does not invoke it. Phase 4.7A and 4.7A.1 AI Model Orchestrator Contracts and Hardening are **IMPLEMENTED**. Phase 4.7B AI Model Runtime Foundation is **IMPLEMENTED**. Phase 4.7C.1 Ollama Model Adapter is **IMPLEMENTED IN ISOLATION**; Production Runtime Cutover is **NOT IMPLEMENTED**, Legacy Production Ollama Path is **UNCHANGED**, and Prompt Composition Engine is **PLANNED**.

## 12. Architecture Decision Record Index

No standalone ADR files exist in this repository yet. The current decision record is maintained through the implementation notes listed in [Architecture README](./README.md): service/search runtime (004), local-provider boundaries (005), infrastructure boundaries (006), Context Engine ownership (007), graph identity and traversal (008), and graph-runtime ownership (009). Future ADR files should record status, decision, consequences, supersession, and implementation sprint without retroactively inventing decisions.

## 13. Glossary

**Enterprise entity:** normalized project, file, knowledge, person, or infrastructure object. **Canonical identity:** stable ID used for merging. **Provisional identity:** source-scoped ID lacking stronger confirmation. **Provenance:** provider/source attribution. **Evidence:** explicit basis for a relationship/confidence. **Provider:** SDK lifecycle wrapper around a source adapter. **ContextSnapshot:** immutable current relevance record. **GraphNode/GraphEdge:** canonical entity and direct typed connection. **Unresolved reference:** label relationship without stable target ID. **Bounded traversal:** depth/size-limited graph query. **Partial success:** usable output despite a failed subsystem. **Organizational Memory** and **AI context package:** PLANNED future snapshots.
