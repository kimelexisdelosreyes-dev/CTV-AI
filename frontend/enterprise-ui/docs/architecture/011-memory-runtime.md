# Memory Runtime Foundation

Phase 4.4B introduces an in-process, non-persistent memory runtime downstream of the graph runtime. Search adapter orchestration submits a ContextSnapshot and ready GraphRuntimeSession to one application-scoped MemoryRuntimeService.

The contribution adapter accepts only explicit temporal evidence. Phases 4.5 and 4.5B carry eligible source metadata timestamps from local-file, local-knowledge, and local-project providers through graph provenance; each can produce a non-empty `ready` MemorySnapshot. Providers without explicit timestamps remain valid and produce `ready-empty` snapshots without fabricated observations. Provider observation and runtime processing timestamps are excluded.

MemoryBuilder creates readonly observations, timeline entries, records, statistics, and diagnostics only from valid contributions. It does not call search, context, providers, GraphBuilder, external systems, or AI. Session reuse is keyed by context snapshot, graph session, and runtime configuration; stale or cancelled builds never become current.

No persistence, cross-session retention, database, filesystem storage, browser storage, UI, API, AI, analytics, or event sourcing exists. Future retention governance must define source permissions, evidence retention, redaction, and durable storage before persistent Organizational Memory is considered.
