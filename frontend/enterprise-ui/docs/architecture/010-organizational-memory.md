# Organizational Memory Contracts

Phase 4.4A is a contract-only extension point. Organizational Memory is **PLANNED**; there is no runtime service or persistence, and no storage, database, API, UI, retrieval implementation, event sourcing, AI, analytics, or connector is introduced here. There is no runtime or persistence in this phase.

Memory means evidence organized over time. It is not chat history, prediction, AI reasoning, enterprise truth, preference storage, a generated fact store, summary, or recommendation engine.

## Model

`Observation -> MemoryEvent -> TimelineEntry -> MemoryRecord -> MemoryRecall`

- An Observation is an explicit provider, graph, context, or import fact with graph identity, timestamp, evidence, confidence, participants, and diagnostics.
- A MemoryEvent deterministically aggregates observations; it does not infer a business event.
- TimelineEntry orders references to graph entities, observations, and events without duplicating graph entities.
- MemoryRecord organizes evidence, temporal relationships, and references. It owns no files, projects, knowledge, infrastructure, graph topology, search execution, providers, or AI.
- Recall and query contracts describe deterministic retrieval only. They do not summarize or rank with AI.

## Evidence, Confidence, and Relationships

All records trace to `MemoryEvidence`, which references observations, events, timelines, providers, or graph identities. Confidence is evidence-derived: confirmed, supported, observed, imported, or unknown. Memory relationships are temporal and distinct from structural graph edges.

## Snapshot and Boundaries

`MemorySnapshot` is readonly and contains observations, events, timeline entries, records, statistics, diagnostics, version, timestamps, and optional graph/runtime references. Contracts reference graph IDs only; memory never owns GraphBuilder, RelationshipGraph, SearchService, provider SDK, React, or presentation.

Future runtime direction is `GraphRuntimeSession -> MemoryBuilder -> MemorySnapshot`, but MemoryBuilder is an **EXTENSION POINT** only. Any future implementation must preserve evidence, immutable public structures, source attribution, deterministic recall, and explicit authorization boundaries.
