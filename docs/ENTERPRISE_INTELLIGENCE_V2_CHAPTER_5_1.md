# Enterprise Intelligence V2 Chapter 5.1

## Provider Architecture

Nexus is integrated as `NexusProvider`, a static Atlas provider registered during
Atlas runtime construction. Atlas sees only standard provider results. Forge and
the AI Router do not know Nexus exists.

## Graph Model

`NexusGraphResult` is immutable and canonically serializable. It contains bounded
entities, relationships, paths, confidence, source references, graph version,
and graph fingerprint.

## Traversal

The provider supports entity lookup, relationship lookup, neighborhood traversal,
and path discovery. Traversal is deterministic and bounded by configured depth
and item limits.

## Limits

Configuration controls maximum entities, maximum relationships, maximum
traversal depth, and maximum execution time. Limit violations are returned as
safe partial provider results.

## Diagnostics

Diagnostics expose graph version, provider status, query count, average latency,
success rate, timeout count, and aggregate entity/relationship counts. They do
not expose graph contents.

## Observability

Nexus metrics are in-memory and read-only. Query count, latency, timeout count,
entity count, relationship count, and success rate are available for future
dashboard integration.

## Future Graph Evolution

The provider boundary allows future Nexus graph backends without changing Atlas
compiler, Forge, prompt construction, or provider result contracts.
