# Enterprise Temporal Evidence

Phase 4.5 preserves explicit, provider-independent temporal evidence from normalized search results through `ContextSnapshot`, graph provenance, and the in-process memory runtime. Providers contribute evidence; Memory interprets eligible evidence into observations. No provider imports Memory contracts or runtime services.

## Semantics and Policy

The supported vocabulary is deliberately small: `created` and `modified`. Each item declares a timestamp category: `source-event`, `source-metadata`, `provider-observation`, or `runtime-processing`. Only source-event and source-metadata evidence is eligible for organizational observations. Provider observation and runtime-processing time remain traceable categories but are excluded from Memory.

Timestamps are accepted only as ISO date or UTC datetime values. Date-only timestamps retain `date` precision; UTC datetimes retain minute, second, or millisecond precision. A missing timezone is rejected rather than interpreted in the local machine timezone. Invalid and missing timestamps are omitted without breaking search.

Evidence IDs are deterministic: provider ID, source entity ID, semantic type, timestamp, and source reference ID. Titles, array positions, runtime time, and raw payloads are never identity inputs. Confidence is `observed` for the current local source-metadata adapter; future authoritative event sources may use `confirmed` or `supported` only when their source semantics justify it.

## Active Provider Coverage

`local-files`, `local-knowledge`, and `local-projects` contribute explicit source-metadata evidence with stable local-demo source-record references. File modification does not claim editorial revision; project current status does not create status history; and knowledge indexing time is excluded. Infrastructure providers currently expose no explicit source timestamps and correctly contribute no temporal evidence. No paths, contents, credentials, raw payloads, personal activity trails, or telemetry payloads are retained by this model.

## Propagation and Runtime

`SearchResult.temporalEvidence` is optional and readonly. Context deduplicates evidence by deterministic ID, orders it deterministically, and exposes it on the immutable snapshot. Graph provenance attaches evidence to the matching node without adding graph nodes or edges. `MemoryContributionAdapter` maps eligible `created` and `modified` evidence only when graph identity, provider attribution, timestamp, and source reference are present. `MemoryBuilder` remains evidence-first, creates deterministic observations and timeline entries, and leaves events empty.

Diagnostics are serializable and limited to identifiers and categories: missing/invalid timestamp, missing timezone, preserved/dropped evidence, unsupported type, incomplete evidence, and memory eligibility. There is no persistence, database, filesystem write, browser storage, API, AI, analytics, or event sourcing. Future live connectors must preserve their declared source timestamps and references without substituting provider fetch or processing time.
