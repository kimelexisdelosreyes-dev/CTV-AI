# Enterprise Intelligence V2 Chapter 5.1.1

## Existing Checkpoint K Baseline

Nexus is already integrated strictly as an Atlas provider. Atlas receives only
standard provider results, while Forge and the AI Router remain Nexus-blind.

## K.1 Architecture

K.1 hardens graph infrastructure before enterprise connectors exist. Future
sources will emit connector-neutral import batches, `NexusGraphBuilder` will
validate and build immutable snapshots, and `NexusGraphStore` will publish one
active snapshot for `NexusProvider` queries.

## Graph Identity Model

Entity IDs are deterministic from namespace, entity type, and normalized
external key. Relationship IDs are deterministic from namespace, source entity,
relationship type, target entity, and optional discriminator. IDs never use
object identity, random UUIDs, timestamps, or import order.

## Schema Versioning

`NexusGraphSchemaVersion` records explicit major/minor versions. Unsupported
versions fail safely and no implicit fallback is allowed.

## Import Contracts

`NexusEntityInput`, `NexusRelationshipInput`, and `NexusGraphImportBatch` are
immutable, canonical, connector-neutral contracts. They carry JSON-safe bounded
metadata only and no connector objects, handles, callbacks, or persistence.

## Builder Lifecycle

`NexusGraphBuilder` accepts explicit import batches, normalizes identities,
deduplicates exact duplicates, rejects conflicting duplicates, validates
relationship endpoints, enforces limits, constructs deterministic indexes, and
produces immutable `NexusGraphSnapshot` instances.

## Immutable Snapshot

`NexusGraphSnapshot` contains canonical entities, relationships, indexes, source
summary, versions, counts, and graph fingerprint. Indexes are included in
canonical serialization to make snapshot bytes directly comparable.

## Duplicate Policy

Exact duplicate entities and relationships are deduplicated. Same deterministic
identity with different canonical content is rejected as a duplicate conflict.
The result is independent of import order.

## Relationship Integrity

Relationships require existing source and target endpoints. Self-references are
rejected by default. Relationship count per entity and metadata size are bounded.

## Deterministic Indexes

Snapshots include entity ID, entity type, relationship ID, outgoing, incoming,
and adjacency indexes. All lookup outputs preserve canonical ordering.

## Graph Store Lifecycle

`NexusGraphStore` holds exactly one active immutable snapshot. Replacement is
explicit and atomic. Failed builds do not replace the current snapshot.

## Atomic Replacement

Readers hold the snapshot object they started with, so concurrent reads complete
against either the old complete snapshot or the new complete snapshot. Partial
snapshots are never published.

## Graph Limits

K.1 enforces maximum import batches, entities, relationships, metadata bytes,
entity aliases, relationships per entity, snapshot bytes, and build duration.

## Fingerprint Design

Snapshot fingerprints include schema version, graph format version, builder
version, fingerprint version, canonical entities, canonical relationships,
canonical indexes, and source summary. They exclude timestamps, metrics, object
addresses, memory usage, and import order.

## Observability

Nexus observability includes build counts, build success/failure, average build
latency, active counts, snapshot replacements, duplicate deduplication, duplicate
conflicts, and limit rejections. It exposes no graph content.

## Diagnostics

Diagnostics expose readiness, schema version, graph version, safe fingerprint
prefix, active counts, build counts, replacement count, average build latency,
and provider status. They do not expose entities, relationships, source IDs,
metadata, import batches, or enterprise content.

## Benchmark Results

`benchmark_nexus_graph_infrastructure.py` measures import validation, identity
generation, duplicate detection, relationship validation, index construction,
serialization, fingerprint generation, replacement, and query latency for small
and moderate graphs.

## Test Results

Focused K.1 tests validate identity, schema, imports, builder behavior,
snapshots, duplicate policy, integrity, indexes, store lifecycle, replacement,
limits, fingerprints, permutations, concurrency, diagnostics, observability, and
provider compatibility.

## Remaining Limitations

K.1 does not connect real enterprise sources, persist graphs, expose public
APIs, add frontend dashboards, or add graph reasoning. K.2 will introduce
enterprise connectors using these import contracts.
