# Temporal Evidence Provider Expansion

Phase 4.5B expands the Phase 4.5 evidence pipeline without changing provider, graph, or Memory ownership. Providers normalize explicit source facts into `TemporalEvidence`; Context and graph preserve those facts generically; Memory creates observations only from eligible evidence.

## Provider Audit

| Provider | Audited | Temporal Evidence | Memory Eligible | Notes |
| --- | --- | --- | --- | --- |
| `local-files` | Yes | `modified`, source metadata | Yes | Filesystem-like metadata; modification is not editorial revision. |
| `local-knowledge` | Yes | `modified`, source metadata | Yes | Explicit local-demo document metadata only; indexing time is excluded. |
| `local-projects` | Yes | `created`, source metadata | Yes | Date-only source metadata; current status and due dates are not history. |
| `workstations` | Yes | None | No | Current inventory/activity has no explicit source timestamp. |
| `infrastructure` | Yes | None | No | Status and health-like activity are operational state, not historical evidence. |
| `storage` | Yes | None | No | Inventory source has no explicit timestamp beyond local-files metadata. |
| `compute` | Yes | None | No | No explicit job or inventory timestamp. |
| `demo-search` | Yes | None | No | Presentation adapter metadata has no temporal source contract. |

The three enriched provider categories use stable record references and the shared deterministic factory. `created` and `modified` are source-metadata time, use supported confidence, and map to corresponding Memory observations. Timestamp-less or operational providers remain valid and evidence-free.

## Timestamp and Privacy Policy

Source metadata and source event time may be memory-eligible. Provider observation and runtime processing time are excluded. ISO date-only values retain date precision; UTC datetimes retain their supplied precision. Timezone-less values are rejected rather than interpreted locally. No due date, current status, owner, assignee, display title, indexing time, health check, or last-seen value becomes an event.

Evidence retains only deterministic identity, provider ID, controlled source reference, timestamp, semantic type/category, precision, and confidence. It does not retain document contents, titles, paths, account IDs, private URLs, employee activity, credentials, or raw source payloads. Filesystem metadata remains subject to copy/reset, metadata-operation, access-time, and NAS timezone caveats.

## Statistics and Telemetry

Context snapshots expose frozen deterministic counts for providers, evidence, entities, semantic categories, and memory eligibility. Memory sessions add observation and ready/ready-empty counts. Optional telemetry emits only count-based `memory_runtime_ready` or `memory_runtime_ready_empty` events. Telemetry is wrapped so sink failures cannot affect search, graph, or Memory correctness.

No persistence, storage, APIs, UI, AI, analytics conclusions, behavioral profiling, or event sourcing is introduced. Remaining provider coverage is limited to local-demo contracts; future connectors must supply explicit source timestamps and stable references before they can contribute evidence.
