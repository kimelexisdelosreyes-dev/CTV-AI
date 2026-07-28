# Graph Runtime Integration

The search presentation adapter is the application-level coordinator. It receives normalized search output, creates an immutable ContextSnapshot, and submits it to the application-scoped GraphRuntimeService. Search presentation does not wait on graph-specific UI rendering and remains functional if graph construction fails.

GraphRuntimeService owns the current immutable session, versioning, reuse of the same source snapshot, invalidation, reset, cancellation checks, and bounded graph queries. ContextEngine remains graph-independent; the handoff is one-way through ContextSnapshot.

Selected search results are resolved through canonical graph IDs, source IDs, aliases, and existing provisional identities. Display titles are not an authoritative resolver. `GraphRuntimeQueryService` returns a depth-one neighborhood from the current session only, and `GraphPresentationAdapter` makes graph rows primary while retaining normalized relationship fallback rows. Selection changes query the current session and do not rebuild the graph.
