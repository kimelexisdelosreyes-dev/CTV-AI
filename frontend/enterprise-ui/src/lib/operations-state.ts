import type {
  ConnectorHealth,
  ConnectorProject,
  ConnectorTask,
  OperationsSnapshotResponse,
  OperationsSyncStatusResponse,
} from "@/lib/api";

export const OPERATIONS_REFRESH_TTL_MS = 120_000;

export type OperationsFilters = {
  query: string;
  board: string;
  status: string;
  priority: string;
};

export type OperationsState = {
  health: ConnectorHealth[];
  projects: ConnectorProject[];
  tasks: ConnectorTask[];
  loading: boolean;
  refreshing: boolean;
  error: string;
  lastUpdated: string | null;
  snapshotId: string | null;
  freshness: "fresh" | "stale" | "refreshing" | "failed" | "empty";
  snapshotLoaded: boolean;
  syncStatus:
    | "idle"
    | "running"
    | "success"
    | "failed"
    | "stale"
    | "suspicious_empty";
  syncMessage: string;
  syncStartedAt: string | null;
  filters: OperationsFilters;
};

export function initialOperationsState(): OperationsState {
  return {
    health: [],
    projects: [],
    tasks: [],
    loading: false,
    refreshing: false,
    error: "",
    lastUpdated: null,
    snapshotId: null,
    freshness: "empty",
    snapshotLoaded: false,
    syncStatus: "idle",
    syncMessage: "",
    syncStartedAt: null,
    filters: {
      query: "",
      board: "all",
      status: "all",
      priority: "all",
    },
  };
}

export function operationsSnapshotIsStale(
  lastUpdated: string | null,
  now: number,
  ttlMs = OPERATIONS_REFRESH_TTL_MS,
): boolean {
  if (!lastUpdated) return true;
  return now - new Date(lastUpdated).getTime() > ttlMs;
}

export function stateFromServerSnapshot(
  current: OperationsState,
  snapshot: OperationsSnapshotResponse,
): OperationsState {
  const preservePopulatedSnapshot =
    current.tasks.length > 0 &&
    snapshot.tasks.length === 0 &&
    snapshot.status !== "empty";
  const health: ConnectorHealth[] = [
    {
      name: "monday",
      status:
        snapshot.freshness === "fresh"
          ? "healthy"
          : snapshot.freshness === "empty"
            ? "unavailable"
            : "degraded",
      checked_at: snapshot.fetched_at ?? new Date().toISOString(),
      latency_ms: null,
      detail:
        snapshot.freshness === "empty"
          ? "No operations snapshot yet."
          : `Server snapshot is ${snapshot.freshness}.`,
    },
  ];
  return {
    ...current,
    health,
    projects: preservePopulatedSnapshot ? current.projects : snapshot.projects,
    tasks: preservePopulatedSnapshot ? current.tasks : snapshot.tasks,
    loading: false,
    refreshing: false,
    error: "",
    lastUpdated: preservePopulatedSnapshot
      ? current.lastUpdated
      : snapshot.fetched_at,
    snapshotId: preservePopulatedSnapshot
      ? current.snapshotId
      : snapshot.snapshot_id,
    freshness: preservePopulatedSnapshot
      ? current.freshness
      : snapshot.freshness,
    snapshotLoaded: true,
    syncStatus: preservePopulatedSnapshot ? "suspicious_empty" : current.syncStatus,
    syncMessage: preservePopulatedSnapshot
      ? "Latest refresh returned no tasks, so the previous snapshot is being shown."
      : current.syncMessage,
  };
}

export function stateAfterRefreshFailure(
  current: OperationsState,
  error: string,
): OperationsState {
  return {
    ...current,
    loading: false,
    refreshing: false,
    error,
  };
}

export function stateFromSyncStatus(
  current: OperationsState,
  status: OperationsSyncStatusResponse,
): OperationsState {
  const failedWithSnapshot = status.status === "failed" && current.lastUpdated;
  return {
    ...current,
    refreshing: status.running,
    syncStatus: status.status,
    syncStartedAt: status.started_at,
    syncMessage: status.running
      ? "Refreshing monday data..."
      : status.status === "suspicious_empty"
        ? status.safe_error ?? "Previous operations snapshot is being shown."
      : status.stale_running_recovered
        ? "Interrupted refresh recovered."
        : "",
    error: status.running
      ? ""
      : failedWithSnapshot
        ? status.safe_error ?? "Latest refresh failed."
        : current.error,
    freshness:
      status.latest_snapshot_status === "refreshing"
        ? current.freshness
        : status.latest_snapshot_status,
  };
}
