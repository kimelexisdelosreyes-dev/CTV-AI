# Enterprise Intelligence v2 - Chapter 5.1.2

## Checkpoint K.2 - Nexus Enterprise Knowledge Ingestion

K.1 established deterministic Nexus graph infrastructure: schema versioning,
connector-neutral import batches, graph building, immutable snapshots,
fingerprints, atomic graph-store replacement, limits, diagnostics, observability,
and concurrency-safe readers.

K.2 adds the ingestion layer in front of K.1. It performs deterministic
ingestion and graph publication. It does not add graph reasoning, semantic graph
ranking, AI-generated relationships, unrestricted live source crawling, public
ingestion APIs, frontend work, external queues, or persistence.

K.3 will focus on graph retrieval quality, bounded multi-hop reasoning, and
Atlas context optimization.

## Dependency Direction

Approved source repositories feed `NexusConnector` implementations. Connectors
produce immutable `NexusConnectorResult` values. The
`NexusIngestionPlanner` creates explicit deterministic plans. The
`NexusIngestionService` owns connector execution, import batch construction,
candidate graph validation, and atomic publication through `NexusGraphStore`.

Connectors do not mutate `NexusGraphStore`, call `NexusProvider`, call Atlas
compiler code, call Forge, call the AI Router, load arbitrary modules, crawl
filesystems, connect to SMB shares, or ingest file bytes.

## Connector Protocol

`NexusConnector` is a connector-neutral protocol with:

- `definition()`
- `initialize()`
- `health()`
- `collect(request)`
- `diagnostics()`

A connector is not an Atlas provider. It produces normalized source records and
tombstones through immutable contracts.

## Connector Definitions

`NexusConnectorDefinition` is immutable and canonical. It contains stable
identity, connector version, source type, supported schema, default budget,
record limits, mode support, deletion support, and default enablement. It
contains no credentials, repository instances, source content, or runtime
objects.

## Collection Contracts

K.2 adds immutable request, cursor, normalized record, tombstone, warning,
failure, metrics, and result contracts. Results are bounded, JSON-safe,
deterministic, and content-free outside approved normalized metadata.

## Normalized Source Records

`NexusNormalizedSourceRecord` captures graph-oriented source state:

- stable source record ID
- source type
- record type
- safe label
- stable external key
- parent and related references
- bounded approved metadata
- content fingerprint supplied by the source model
- source version
- deletion state

Full document text, transcript text, OCR text, file bytes, credentials, and
absolute paths are excluded.

## Source Fingerprinting

Source fingerprints include connector identity/version, normalized source
records, approved metadata, source versions, content fingerprints, and
tombstones. They exclude runtime duration, timestamps, process identity,
database row order, pagination order, credentials, and transient repository
details.

## Registry

`NexusConnectorRegistry` is explicit and static. It rejects duplicate connector
IDs, returns connectors in canonical order, exposes safe readiness, and supports
deterministic selection. It does not implement plugin installation or arbitrary
module loading.

## Planning

`NexusIngestionPlanner` produces immutable `NexusIngestionPlan` values. Plans
select connectors, preserve required/optional status, set import mode, bound
source records, apply connector budgets, and declare whether publication is
allowed. The planner never executes connectors and never modifies graph state.

## Import Modes

`FULL` stages a complete bounded source state and can publish a complete
snapshot.

`INCREMENTAL` applies connector deltas and tombstones against retained
content-minimized source state, then rebuilds a complete candidate snapshot.
If safe retained state is unavailable, it fails without publication.

`VALIDATE_ONLY` performs extraction, mapping, batch creation, and candidate
graph validation without publishing.

## Tombstones And Ownership

`NexusSourceTombstone` is deterministic and content-free. Tombstones remove
source-owned records from staged source state, independent of tombstone order.

Graph input metadata records internal ownership: connector ID, source record ID,
source version, source fingerprint, and record type. This ownership is retained
inside import infrastructure and is not exposed through Atlas provider output.

## Ingestion Service

`NexusIngestionService` executes explicit plans independent of request-time
Atlas execution. It enforces connector failures and deadlines, collects results,
maps records to `NexusGraphImportBatch`, applies tombstones, builds a complete
candidate snapshot with `NexusGraphBuilder`, compares fingerprints, publishes
atomically when required, records content-free outcomes, and preserves the
active snapshot on failure.

No provider query triggers ingestion implicitly.

## Transaction Lifecycle

1. Create plan.
2. Collect connector results.
3. Validate source fingerprints.
4. Build candidate import batches.
5. Apply deterministic tombstones.
6. Construct candidate snapshot.
7. Validate candidate snapshot.
8. Compare fingerprints.
9. Publish atomically or retain the current snapshot.

## Rollback And History

K.2 retains at most the active snapshot and the immediately previous published
snapshot in memory. Rollback is explicit and bounded.

`NexusIngestionHistory` stores bounded content-free outcomes: operation ID,
connector IDs, mode, status, counts, safe failure category, duration, fingerprint
prefix, and operational timestamp. It does not store titles, paths, labels,
metadata, snapshots, credentials, or source content.

## First-Party Connectors

`CompanyBrainNexusConnector` uses an approved read-only Company Brain repository
protocol and maps existing document metadata into records. It does not call API
routes, duplicate ingestion jobs, or retain full content. The mapper creates
knowledge document and collection entities plus explicit collection
relationships when category data exists.

`ArchiveMetadataNexusConnector` uses an explicit read-only archive metadata
repository protocol and deterministic fixture adapter patterns. It does not
crawl filesystems, scan NAS devices, connect to SMB shares, use credentials, or
read file bytes. The mapper creates media asset/project entities and direct
metadata-supported relationships.

## Observability And Diagnostics

K.2 records content-free ingestion and connector metrics: run counts, success
and failure counts, validate-only count, no-change count, publication count,
rollback count, average latencies, connector counts, record counts, tombstone
counts, and snapshot byte counts.

Diagnostics expose ingestion enabled state, last safe status, last mode, active
graph version, fingerprint prefix, previous snapshot availability, connector
count, connector health states, aggregate counts, average latency, and bounded
history size.

Diagnostics do not expose source record IDs, document titles, filenames, paths,
entity labels, relationship contents, raw metadata, repository details, raw
exceptions, credentials, prompts, OCR, transcripts, or document bodies.

## Benchmark

`backend/scripts/benchmark_nexus_ingestion.py` measures deterministic fixtures
for Company Brain extraction/mapping, archive extraction/mapping, source
fingerprinting, planning, import batch creation, graph build, validation,
publication, no-change ingestion, incremental ingestion, snapshot bytes,
records per second, and provider query latency.

## Tests

Focused K.2 tests validate immutable contracts, registry behavior, health,
source fingerprinting, planning, full import, incremental import, validate-only,
tombstones, ownership-safe mapping, multi-source determinism, 100 repeated
ingestions, 100 permutations, concurrent readers, rollback, bounded history,
privacy, and dependency boundaries.

## Limitations

K.2 remains in-memory and explicitly invoked. Incremental ingestion requires a
safe retained source-state manifest from a prior full import. Archive metadata
uses a read-only protocol and deterministic fixture adapter because no stable
archive repository exists in the current backend.

