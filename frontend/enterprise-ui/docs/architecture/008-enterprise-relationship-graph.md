# Enterprise Relationship Graph

The graph is an in-memory, deterministic read model built from ContextSnapshot entities and direct relationships. It has canonical IDs, provenance, provisional identity flags, immutable snapshots, stable ordering, and bounded BFS traversal (default depth 1, maximum depth 3).

It does not call providers, SearchService, ContextEngine, databases, AI, memory, or external systems. Context flows one way through `ContextGraphAdapter` into `GraphBuilder`. Unresolved presentation-only targets are intentionally not fabricated as graph nodes.
