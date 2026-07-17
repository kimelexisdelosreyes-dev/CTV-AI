import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(
  new URL("../src/lib/operations-state.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
});
const moduleUrl = `data:text/javascript;base64,${Buffer.from(
  compiled.outputText,
).toString("base64")}`;
const {
  initialOperationsState,
  operationsSnapshotIsStale,
  stateAfterRefreshFailure,
  stateFromServerSnapshot,
  stateFromSyncStatus,
} = await import(moduleUrl);

test("initial operations state has no snapshot and default filters", () => {
  const state = initialOperationsState();

  assert.equal(state.tasks.length, 0);
  assert.equal(state.lastUpdated, null);
  assert.equal(state.snapshotLoaded, false);
  assert.deepEqual(state.filters, {
    query: "",
    board: "all",
    status: "all",
    priority: "all",
  });
});

test("fresh operations snapshot does not require refetch", () => {
  const now = Date.parse("2026-07-17T00:02:00Z");
  const updated = "2026-07-17T00:01:30Z";

  assert.equal(operationsSnapshotIsStale(updated, now, 120_000), false);
});

test("stale operations snapshot refreshes in background", () => {
  const now = Date.parse("2026-07-17T00:05:00Z");
  const updated = "2026-07-17T00:01:00Z";

  assert.equal(operationsSnapshotIsStale(updated, now, 120_000), true);
});

test("missing operations snapshot is stale", () => {
  assert.equal(operationsSnapshotIsStale(null, Date.now(), 120_000), true);
});

test("server snapshot replaces tasks and records freshness", () => {
  const state = stateFromServerSnapshot(initialOperationsState(), {
    snapshot_id: "snapshot-1",
    status: "success",
    freshness: "stale",
    fetched_at: "2026-07-17T00:00:00Z",
    tasks: [{ external_id: "task-1", title: "Edit", metadata: {} }],
    projects: [{ external_id: "board-1", name: "Production", metadata: {} }],
  });

  assert.equal(state.tasks[0].title, "Edit");
  assert.equal(state.snapshotId, "snapshot-1");
  assert.equal(state.freshness, "stale");
  assert.equal(state.health[0].status, "degraded");
});

test("empty successful response cannot replace populated client state", () => {
  const current = {
    ...initialOperationsState(),
    snapshotId: "snapshot-1",
    tasks: [{ external_id: "task-1", title: "Keep me", metadata: {} }],
    projects: [{ external_id: "board-1", name: "Production", metadata: {} }],
    lastUpdated: "2026-07-17T00:00:00Z",
    freshness: "fresh",
  };
  const state = stateFromServerSnapshot(current, {
    snapshot_id: "snapshot-2",
    status: "success",
    freshness: "fresh",
    fetched_at: "2026-07-17T00:05:00Z",
    task_count: 0,
    tasks: [],
    projects: [{ external_id: "board-2", name: "Empty", metadata: {} }],
  });

  assert.equal(state.tasks[0].title, "Keep me");
  assert.equal(state.projects[0].name, "Production");
  assert.equal(state.snapshotId, "snapshot-1");
  assert.equal(state.syncStatus, "suspicious_empty");
  assert.match(state.syncMessage, /previous snapshot/i);
});

test("refresh failure preserves the previous snapshot", () => {
  const current = {
    ...initialOperationsState(),
    tasks: [{ external_id: "task-1", title: "Keep me", metadata: {} }],
    lastUpdated: "2026-07-17T00:00:00Z",
    refreshing: true,
  };

  const failed = stateAfterRefreshFailure(current, "Safe refresh error");

  assert.equal(failed.tasks[0].title, "Keep me");
  assert.equal(failed.lastUpdated, current.lastUpdated);
  assert.equal(failed.refreshing, false);
  assert.equal(failed.error, "Safe refresh error");
});

test("empty snapshot produces an unavailable connector state", () => {
  const state = stateFromServerSnapshot(initialOperationsState(), {
    snapshot_id: null,
    status: "empty",
    freshness: "empty",
    fetched_at: null,
    tasks: [],
    projects: [],
  });

  assert.equal(state.tasks.length, 0);
  assert.equal(state.freshness, "empty");
  assert.equal(state.health[0].status, "unavailable");
  assert.equal(state.snapshotLoaded, true);
});

test("running sync clears failure banner and disables refresh", () => {
  const current = {
    ...initialOperationsState(),
    error: "Old failure",
    lastUpdated: "2026-07-17T00:00:00Z",
  };
  const state = stateFromSyncStatus(current, {
    state: "running",
    running: true,
    status: "running",
    started_at: "2026-07-17T00:01:00Z",
    last_success_at: current.lastUpdated,
    last_failure_at: null,
    latest_snapshot_id: "snapshot-1",
    latest_snapshot_age_seconds: 60,
    latest_snapshot_status: "refreshing",
    safe_error: null,
    can_refresh: false,
    stale_running_recovered: false,
  });

  assert.equal(state.refreshing, true);
  assert.equal(state.error, "");
  assert.equal(state.syncMessage, "Refreshing monday data...");
});

test("failed sync keeps snapshot and shows safe failure", () => {
  const current = {
    ...initialOperationsState(),
    tasks: [{ external_id: "task-1", title: "Keep me", metadata: {} }],
    lastUpdated: "2026-07-17T00:00:00Z",
  };
  const state = stateFromSyncStatus(current, {
    state: "idle",
    running: false,
    status: "failed",
    started_at: null,
    last_success_at: current.lastUpdated,
    last_failure_at: "2026-07-17T00:02:00Z",
    latest_snapshot_id: "snapshot-1",
    latest_snapshot_age_seconds: 120,
    latest_snapshot_status: "fresh",
    safe_error: "Latest refresh failed safely.",
    can_refresh: true,
    stale_running_recovered: false,
  });

  assert.equal(state.tasks[0].title, "Keep me");
  assert.equal(state.error, "Latest refresh failed safely.");
  assert.equal(state.refreshing, false);
});

test("suspicious empty sync keeps tasks and shows retention warning", () => {
  const current = {
    ...initialOperationsState(),
    tasks: [{ external_id: "task-1", title: "Keep me", metadata: {} }],
    lastUpdated: "2026-07-17T00:00:00Z",
  };
  const state = stateFromSyncStatus(current, {
    state: "idle",
    running: false,
    status: "suspicious_empty",
    started_at: null,
    last_success_at: current.lastUpdated,
    last_failure_at: "2026-07-17T00:02:00Z",
    latest_snapshot_id: "snapshot-1",
    latest_snapshot_age_seconds: 120,
    latest_snapshot_status: "fresh",
    safe_error: "Latest refresh returned no tasks, so the previous snapshot is being shown.",
    can_refresh: true,
    stale_running_recovered: false,
  });

  assert.equal(state.tasks[0].title, "Keep me");
  assert.equal(state.error, "");
  assert.equal(state.syncStatus, "suspicious_empty");
  assert.match(state.syncMessage, /previous snapshot/i);
});
