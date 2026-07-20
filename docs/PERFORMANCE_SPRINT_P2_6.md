# P2.6 Monday Snapshot Reliability and Observability

## Snapshot lifecycle

Every refresh uses the same `OperationsSnapshotService.sync()` path, whether triggered manually, at startup, or by the scheduler.

1. Acquire the in-process guard and PostgreSQL advisory lock.
2. Commit a `pending` refresh-attempt row. It is never visible to Company Brain.
3. Fetch Monday tasks and projects with bounded retry handling.
4. Deduplicate and normalize tasks, validate suspicious empty results, and calculate a deterministic content hash.
5. Insert candidate tasks and verify the inserted count.
6. In one transaction, retire the previous `active` row and mark the validated candidate `active`.
7. After activation, invalidate operations cache entries only when the content hash changed.
8. Record safe refresh and invalidation diagnostics.

The partial unique index `uq_operations_snapshots_one_active` enforces one active row. A failed write rolls back candidate tasks and cannot retire the previous active snapshot.

## Lock strategy

Refreshes use PostgreSQL session advisory lock `0x43545632`, held across fetch, validation, candidate write, activation, and post-activation invalidation. A second process receives the existing safe `operations_sync_in_progress` response. The lock is released in `finally` on success, failure, cancellation, or exception. The in-process lock remains as a fast local guard, but correctness does not depend on it.

## Content hash

The SHA-256 hash uses stable sorted task and project data. Task identity, title, status, priority, deadline, assignees, board/group, project, and URL are included. Project identity, name, status, owners, and URL are included. Fetch time and Monday `updated_at` metadata are excluded. Identical content therefore retains the same operations semantic-cache fingerprint even though freshness timestamps and active snapshot identity change.

## Freshness and last known-good behavior

- `fresh`: age at or below `CTV_ONE_OPERATIONS_SNAPSHOT_FRESH_SECONDS`.
- `aging`: older than fresh and at or below `CTV_ONE_OPERATIONS_SNAPSHOT_AGING_SECONDS`.
- `stale`: older than the aging threshold; it remains usable as last known-good data.
- `unavailable`: no active snapshot exists.

Pending and failed candidates are ignored by request-time retrieval. A failed refresh records a safe category and timestamp while the existing active snapshot remains available. Suspicious empty results are rejected when a non-empty active snapshot exists.

## Retry policy

The default is three attempts with exponential delays starting at 0.5 seconds and capped at 10 seconds. Network failures, timeouts, HTTP 429, and HTTP 5xx are retryable. Authentication, configuration, malformed payload, and GraphQL validation failures are not retried. Logs contain safe categories and aggregate attempt counts, never tokens or raw Monday responses.

## Scheduler

The minimal in-process scheduler is controlled by:

- `CTV_ONE_MONDAY_SNAPSHOT_REFRESH_ENABLED`
- `CTV_ONE_MONDAY_SNAPSHOT_REFRESH_INTERVAL_SECONDS`
- `CTV_ONE_MONDAY_SNAPSHOT_REFRESH_ON_STARTUP`

Startup refresh is disabled by default. Scheduler exceptions are contained and do not terminate the API. Manual and scheduled refreshes share the central service. Multiple API processes may each run a scheduler task, but the PostgreSQL advisory lock prevents overlapping refresh work; a distributed scheduler remains deferred.

## Cache invalidation

The semantic cache operations fingerprint is the active snapshot `content_hash`, not snapshot ID or fetch timestamp. Activation happens before invalidation. Changed content deletes operations-dependent entries and records the count. Identical content preserves entries. Failed or pending refreshes cannot alter the active fingerprint and cause zero invalidations.

## Diagnostics and manual refresh

Safe endpoints:

- `GET /api/v1/operations/snapshot/status`
- `POST /api/v1/operations/snapshot/refresh`
- Existing `/operations/sync/status` and `/operations/refresh` paths remain available.

Status includes active ID, generated/activated timestamps, age, freshness, task and board counts, a 12-character hash prefix, last refresh/failure status, duration, running state, content-change state, and cache invalidation count. It never includes raw tasks, raw upstream responses, credentials, or tokens. Manual refresh requires an admin or manager.

## Failure recovery

Correct Monday configuration or network/authentication problems, then invoke manual refresh or wait for the scheduler. Stale `pending` attempts are marked failed after the configured refresh timeout and grace period. No cleanup operation is required to restore the last active snapshot because it is never replaced on failure.

## Migration and limitations

Apply Alembic revision `0011`. It converts the newest legacy `success` row to `active`, retires older successful rows, converts interrupted `running` rows to `pending`, adds lifecycle metadata, and creates the one-active partial unique index.

The scheduler is intentionally in-process, retries rerun the complete Monday fetch, and cache invalidation is operations-wide rather than candidate-specific. Distributed scheduling and queueing remain out of scope.
