# Chapter 3 Sprint 3.2 — Checkpoint B

Checkpoint B defines Atlas compiler contracts only. Atlas remains dormant: no provider is implemented, no retrieval or inference occurs, and no production request path imports compiler contracts.

## Contract architecture

`AtlasContextRequest` describes a provider-independent compile intent. `AtlasCompilationSnapshot` captures every eventual compiler input, including a caller-supplied compilation time, access snapshot, immutable policy, deterministic provider plan, and supplied provider inputs. The compiler will read only this snapshot in a later checkpoint.

## AIR and graph boundary

AIR is a flat, immutable, provider-neutral normalization layer. AIR records have provenance, classification, integer confidence, and canonical ordinal fields. Relation candidates remain AIR records; graph construction is deliberately deferred. Graph-ready package models can carry provenance, classification, score, and ordinal data but no graph algorithm has been added.

## Immutability and serialization

Nested JSON-like values use `FrozenJson`: canonical UTF-8 JSON is retained internally and `to_python()` returns a fresh copy. This prevents mutations of caller dictionaries from changing stored contract values. `AtlasCanonicalModel` centralizes canonical dictionary, JSON, bytes, and SHA-256 fingerprint methods. Serialization uses sorted keys, compact separators, UTF-8, timezone-aware timestamps, and rejects non-finite numbers.

## Fingerprints and manifest

Snapshots and policies have deterministic SHA-256 fingerprints. Package deterministic content excludes runtime metrics and clears its self-fingerprint before hashing. The versioned manifest is limited to rule outcomes, stable identifiers, scores, ranks, budget/conflict references, and safe metadata; it contains neither hidden reasoning nor raw context content.

## Package v1.1

New packages default to 1.1 and add snapshot, policy, AIR, conflict, manifest, and fingerprint fields. Valid legacy 1.0 package input remains accepted for compatibility; empty-package construction now produces the deterministic 1.1 shape with a fixed epoch timestamp.

## Checkpoint C compiler engine

`AtlasContextCompiler` is a synchronous, stateless Atlas-only facade. It accepts only an immutable compilation snapshot and executes fixed stages: validation, supplied-input selection, generic AIR normalization, graph construction, conservative exact deduplication, explicit-fact conflict detection, integer scoring, canonical ranking, budget selection, manifest construction, and package construction.

No stage reads runtime configuration, a provider registry, a database, an LLM, or a request object. Generic records can express a relation candidate through stable AIR fields; orphan candidates are omitted with a manifest decision. Exact source-reference/content duplicates are removed conservatively. Conflicts require explicit structured subject/predicate/value attributes and are preserved.

Ranking uses total score, provider priority, confidence, supplied freshness, provider ID, and item ID. Budgeting applies ranked node, per-provider node, relationship, and text limits deterministically. All stages emit safe, stable manifest decisions. Runtime integration and metrics publication remain deferred.

## Bounded manifest architecture

The package is a bounded execution artifact, while the full manifest is a separate audit artifact retained by `AtlasCompilationResult`. A package carries only an immutable manifest reference: digest, version, and bounded counts. Fingerprints are non-recursive: snapshot and policy fingerprints produce the full manifest digest; the package references that digest; the package fingerprint is then calculated; the result digest binds both artifacts. No manifest persistence is introduced.

## Checkpoint C.4 direct-stage validation matrix

| Stage | Test Module | Direct Tests | Status |
|---|---|---:|---|
| Snapshot validation | `test_compiler_validation.py` | 11 | PASS |
| Provider selection | `test_provider_selection.py` | 11 | PASS |
| AIR normalization | `test_air_normalizer.py` | 16 | PASS |
| Graph builder | `test_graph_builder.py` | 16 | PASS |
| Deduplication | `test_deduplication.py` | 12 | PASS |
| Conflict detection | `test_conflicts.py` | 12 | PASS |
| Scoring | `test_scoring.py` | 15 | PASS |
| Ranking | `test_ranking.py` | 12 | PASS |
| Budgets | `test_budgets.py` | 18 | PASS |
| Optimizer | `test_optimizer.py` | 7 | PASS |
| Manifest builder | `test_manifest_builder.py` | 8 | PASS |
| Package builder | `test_package_builder.py` | 10 | PASS |

The 160 tests above call the narrow compiler stage interfaces directly. They use fixed timestamps and synthetic immutable inputs, with no provider registry, database, network, inference, or runtime startup dependency.

## Checkpoint D runtime integration

`AtlasRuntimeManager` owns one stateless compiler for its active lifetime. It constructs the compiler once during enabled initialization or accepts an injected instance for testing. `compile_context()` accepts only an immutable supplied snapshot and does not consult the provider registry or any production service.

Compilation is admitted only while Atlas is enabled and ready. Four bounded synchronous slots allow local concurrent work without modifying the compiler. Shutdown rejects new work and waits boundedly for active calls. Operational attempts, successes, failures, active/peak counts, sanitized error category, timings, package/manifest bytes, selected nodes, and conflicts are stored as thread-safe scalar runtime metrics outside deterministic artifacts.

Diagnostics expose compiler availability, readiness, concurrency limit, contract versions, and safe aggregate metrics. They never expose snapshots, AIR, graph content, manifest decisions, provider payloads, or credentials. Atlas remains disconnected from production request paths, Forge, Nexus, databases, inference, and provider collection.

Checkpoint D validation added 23 focused runtime tests; the Atlas suite passed 221 tests and the full backend passed 498 tests. Forge and Supervisor regressions, release validation, compileall, and whitespace checks passed. Across ten moderate-fixture runs, direct compilation measured 210.247 ms median and runtime-managed compilation measured 235.409 ms median: 25.161 ms / 11.968% orchestration overhead. The additional cost is primarily exact serialization of the separate 509,595-byte manifest for operational size metrics; the 10,919-byte package and all deterministic outputs remain unchanged.
