import type {
  ConnectorHealth,
  ConnectorProject,
  ConnectorTask,
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
