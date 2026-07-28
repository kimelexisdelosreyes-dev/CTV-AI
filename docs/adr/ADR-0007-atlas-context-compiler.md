# ADR-0007: Atlas Context Compiler Contracts

## Decision

Atlas is a deterministic compiler, not a retrieval, memory, RAG, or orchestration service. It compiles supplied inputs only. Its future pipeline normalizes provider-neutral inputs into flat AIR before any graph construction.

Compiler policies use fixed-point integer score contracts. Canonical UTF-8 serialization and SHA-256 fingerprints make equal contract values byte-stable. The manifest records deterministic rule outcomes rather than chain-of-thought or exception details. Nested JSON is retained in immutable canonical form.

## Consequences

Provider implementations, request-path integration, retrieval, databases, LLM calls, Nexus integration, and Forge integration remain outside Checkpoint B. The package evolves to v1.1 while valid legacy v1.0 input remains readable.

AtlasContextPackage is a bounded execution artifact. AtlasContextManifest is a separate in-memory audit artifact carried by AtlasCompilationResult; packages reference its deterministic digest and bounded counts. Persistence is deferred.
