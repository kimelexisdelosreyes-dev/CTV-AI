# Performance Sprint P2.3: Operations Snapshot

## Architecture

monday.com remains the live source, but live retrieval now occurs only during an
operations sync. Successful syncs normalize the configured boards and tasks into
PostgreSQL. Company Brain and the Operations workspace read the latest successful
snapshot and never call monday.com during normal reads.

The `operations_snapshots` table records sync state, safe errors, timestamps,
task counts, compact project metadata, and sync metadata. `operation_tasks`
contains only the normalized fields used by Company Brain and the Operations UI.
No API token, GraphQL response, or raw monday payload is stored.

## Synchronization

The backend starts a non-blocking sync loop when `OPERATIONS_SYNC_ENABLED=true`.
It performs an initial startup refresh and then waits
`OPERATIONS_SYNC_INTERVAL_SECONDS` between attempts. One process-local lock
prevents overlapping startup, background, and manual refreshes. A failed sync is
recorded safely and does not replace or delete the latest successful snapshot.

Configuration:

- `OPERATIONS_SYNC_ENABLED=true`
- `OPERATIONS_SYNC_INTERVAL_SECONDS=300`
- `OPERATIONS_SNAPSHOT_MAX_AGE_SECONDS=300`
- `OPERATIONS_SYNC_TIMEOUT_SECONDS=60`

Manual refresh remains available even when scheduled sync is disabled.
If manual refresh overlaps an active startup or background sync, the API returns
HTTP 202 with the latest snapshot and `Refresh already in progress` instead of a
failure. The UI polls sync status and keeps the existing snapshot visible.

Cancelled jobs are marked failed safely. On restart, a persisted `running` row
older than the configured timeout plus a short grace period is recovered as
failed, allowing a new refresh. The status endpoint reports whether refresh is
currently possible and whether stale-running recovery occurred.

Snapshot promotion is atomic: inserted task rows are counted before the running
snapshot is marked successful, and the committed task relationship is reloaded
before the response is returned. If configured boards are returned with zero
normalized tasks while a populated successful snapshot exists, the attempted
refresh is recorded as `operations_sync_empty_result` and the previous snapshot
is retained. Counts-only pagination and normalization diagnostics are recorded;
task content and upstream payloads are not logged.

## API

- `GET /api/v1/operations/snapshot` returns the latest successful snapshot and
  supports `limit` and `offset` for tasks.
- `POST /api/v1/operations/refresh` performs a guarded live monday sync.
- `GET /api/v1/operations/sync/status` reports running state and safe timestamps.

All endpoints require authentication. Empty state is explicit. Stale snapshots
remain readable and are labeled `stale`; refresh errors keep old tasks visible.

## Company Brain

Operational context preserves overdue filtering, urgency/blocking/due-date
ranking, and prompt caps. It now records snapshot ID, age, freshness, task count,
source, and database fetch duration. When no successful snapshot exists,
operations-required questions return a controlled
`operations_snapshot_unavailable` error instead of silently answering without
operations data.

## Setup and validation

Run `alembic upgrade head` from `backend`, start the API, then call
`POST /api/v1/operations/refresh` with an authenticated request. Confirm
`GET /api/v1/operations/snapshot` returns a snapshot ID and tasks. Company Brain
performance logs should show `operations_context_source=snapshot`; normal asks
should not produce a live sync event.
