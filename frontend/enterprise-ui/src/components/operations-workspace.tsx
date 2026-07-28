"use client";

import {
  Dispatch,
  SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from "react";
import {
  ExternalLink,
  RefreshCw,
} from "lucide-react";

import {
  EmptyState,
  InlineAlert,
  LoadingSkeleton,
  MetricCard,
  PageHeader,
  PageShell,
  PageTitle,
  PrimaryButton,
  SearchInput,
  StatusBadge,
  SyncStatus,
} from "@/design-system";
import {
  apiFetch,
  ConnectorTask,
  OperationsRefreshResponse,
  OperationsSnapshotResponse,
  OperationsSyncStatusResponse,
} from "@/lib/api";
import {
  OperationsFilters,
  OperationsState,
  stateAfterRefreshFailure,
  stateFromServerSnapshot,
  stateFromSyncStatus,
} from "@/lib/operations-state";

type Props = {
  state: OperationsState;
  setState: Dispatch<SetStateAction<OperationsState>>;
};

function sameLocalDay(value: string | null, date: Date): boolean {
  if (!value) return false;
  const parsed = new Date(value);

  return (
    parsed.getFullYear() === date.getFullYear() &&
    parsed.getMonth() === date.getMonth() &&
    parsed.getDate() === date.getDate()
  );
}

function isDone(status: string | null): boolean {
  const value = (status ?? "").toLowerCase();
  return ["done", "complete", "completed", "finished"].some((term) =>
    value.includes(term),
  );
}

function isOverdue(task: ConnectorTask, now: Date): boolean {
  if (!task.due_at || isDone(task.status)) return false;
  return new Date(task.due_at).getTime() < now.getTime();
}

function statusTone(status: string | null): "healthy" | "critical" | "processing" | "neutral" {
  const value = (status ?? "").toLowerCase();

  if (value.includes("done") || value.includes("complete")) {
    return "healthy";
  }
  if (value.includes("stuck") || value.includes("blocked")) {
    return "critical";
  }
  if (value.includes("working") || value.includes("progress")) {
    return "processing";
  }
  return "neutral";
}

function priorityClass(priority: string | null): string {
  const value = (priority ?? "").toLowerCase();

  if (value.includes("critical") || value.includes("urgent")) {
    return "priority-chip priority-critical";
  }
  if (value.includes("high")) return "priority-chip priority-high";
  if (value.includes("medium")) return "priority-chip priority-medium";
  if (value.includes("low")) return "priority-chip priority-low";
  return "priority-chip";
}

export function OperationsWorkspace({ state, setState }: Props) {
  const { health, projects, tasks, loading, refreshing, error, lastUpdated } =
    state;
  const { query, board, status, priority } = state.filters;
  const now = useMemo(() => new Date(), []);
  const loadInFlight = useRef(false);
  const statusInFlight = useRef(false);

  const load = useCallback(async (mode: "initial" | "manual") => {
    if (loadInFlight.current || state.loading || state.refreshing) return;
    loadInFlight.current = true;

    const hasSnapshot = state.lastUpdated !== null;
    setState((current) => ({
      ...current,
      loading: mode === "initial" && !hasSnapshot,
      refreshing: mode !== "initial" || hasSnapshot,
      error: "",
    }));

    try {
      if (mode === "manual") {
        const result = await apiFetch<OperationsRefreshResponse>(
          "/operations/refresh",
          { method: "POST" },
        );
        setState((current) => ({
          ...stateFromServerSnapshot(current, result.snapshot),
          refreshing: result.running,
          syncStatus: result.status,
          syncMessage: result.message,
        }));
      } else {
        const [snapshot, syncStatus] = await Promise.all([
          apiFetch<OperationsSnapshotResponse>("/operations/snapshot"),
          apiFetch<OperationsSyncStatusResponse>("/operations/sync/status"),
        ]);
        setState((current) =>
          stateFromSyncStatus(
            stateFromServerSnapshot(current, snapshot),
            syncStatus,
          ),
        );
      }
    } catch (cause) {
      setState((current) =>
        stateAfterRefreshFailure(
          current,
          cause instanceof Error
            ? cause.message
            : "Could not load monday.com operations data.",
        ),
      );
    } finally {
      loadInFlight.current = false;
    }
  }, [setState, state.lastUpdated, state.loading, state.refreshing]);

  useEffect(() => {
    if (!state.refreshing) return;
    const handle = window.setTimeout(async () => {
      if (statusInFlight.current) return;
      statusInFlight.current = true;
      try {
        const syncStatus = await apiFetch<OperationsSyncStatusResponse>(
          "/operations/sync/status",
        );
        setState((current) => stateFromSyncStatus(current, syncStatus));
        if (!syncStatus.running) {
          const snapshot = await apiFetch<OperationsSnapshotResponse>(
            "/operations/snapshot",
          );
          setState((current) => stateFromServerSnapshot(current, snapshot));
        }
      } catch (cause) {
        setState((current) =>
          stateAfterRefreshFailure(
            current,
            cause instanceof Error
              ? cause.message
              : "Could not check operations refresh status.",
          ),
        );
      } finally {
        statusInFlight.current = false;
      }
    }, 2000);
    return () => window.clearTimeout(handle);
  }, [setState, state.refreshing]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!state.snapshotLoaded) {
        void load("initial");
      }
    }, 0);
    return () => window.clearTimeout(handle);
  }, [load, state.snapshotLoaded]);

  const summary = useMemo(() => {
    const completed = tasks.filter((task) => isDone(task.status)).length;
    const active = tasks.length - completed;
    const dueToday = tasks.filter(
      (task) => !isDone(task.status) && sameLocalDay(task.due_at, now),
    ).length;
    const overdue = tasks.filter((task) => isOverdue(task, now)).length;

    return {
      active,
      dueToday,
      overdue,
      completed,
      boards: projects.length,
    };
  }, [tasks, projects, now]);

  const boardNames = useMemo(
    () =>
      Array.from(
        new Set(
          tasks
            .map((task) => task.metadata.board_name)
            .filter((value): value is string => Boolean(value)),
        ),
      ).sort(),
    [tasks],
  );

  const statusNames = useMemo(
    () =>
      Array.from(
        new Set(
          tasks
            .map((task) => task.status)
            .filter((value): value is string => Boolean(value)),
        ),
      ).sort(),
    [tasks],
  );

  const priorityNames = useMemo(
    () =>
      Array.from(
        new Set(
          tasks
            .map((task) => task.priority)
            .filter((value): value is string => Boolean(value)),
        ),
      ).sort(),
    [tasks],
  );

  const filteredTasks = useMemo(() => {
    const needle = query.toLowerCase().trim();

    return tasks.filter((task) => {
      const boardName = task.metadata.board_name ?? "";
      const groupName = task.metadata.group_title ?? "";
      const searchable = [
        task.title,
        task.status ?? "",
        task.priority ?? "",
        boardName,
        groupName,
        task.assignee_ids.join(" "),
      ]
        .join(" ")
        .toLowerCase();

      return (
        (!needle || searchable.includes(needle)) &&
        (board === "all" || boardName === board) &&
        (status === "all" || task.status === status) &&
        (priority === "all" || task.priority === priority)
      );
    });
  }, [tasks, query, board, status, priority]);

  const mondayHealth = health.find((item) => item.name === "monday");
  const lastChecked = mondayHealth?.checked_at
    ? new Date(mondayHealth.checked_at).toLocaleString()
    : "Not available";
  const updatedLabel = lastUpdated
    ? `Updated ${new Date(lastUpdated).toLocaleString()}`
    : "Not updated yet";

  if (loading) {
    return <LoadingSkeleton lines={7} />;
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="PROJECT INTELLIGENCE"
        title={<PageTitle>Projects</PageTitle>}
        description={
          <p className="ctv-body">
            {updatedLabel}
            {state.freshness === "stale" ? " - Data may be stale" : ""}
            {refreshing ? " - Refreshing..." : ""}
            {state.syncMessage && state.syncStatus !== "suspicious_empty"
              ? ` - ${state.syncMessage}`
              : ""}
          </p>
        }
        action={
          <PrimaryButton
            disabled={refreshing}
            leadingIcon={<RefreshCw size={16} className={refreshing ? "spin" : ""} />}
            onClick={() => load("manual")}
          >
          {refreshing ? "Refreshing..." : "Refresh monday"}
          </PrimaryButton>
        }
      />

      {error && (
        <InlineAlert
          status="critical"
          title={lastUpdated ? "Latest refresh failed" : "Operations refresh failed"}
        >
            {error}
            {lastUpdated && (
              <> Showing data from {new Date(lastUpdated).toLocaleString()}.</>
            )}
        </InlineAlert>
      )}

      {state.syncStatus === "suspicious_empty" && state.syncMessage && (
        <InlineAlert title="Previous snapshot retained" status="warning">
          {state.syncMessage}
        </InlineAlert>
      )}

      {!loading && state.freshness === "empty" && (
        <EmptyState title="No synchronized projects are available.">
          Projects synchronized from Monday.com will appear here.
        </EmptyState>
      )}

      <div className="metric-grid operations-metrics">
        <MetricCard label="Active tasks" value={summary.active} status="processing" />
        <MetricCard label="Due today" value={summary.dueToday} status="warning" />
        <MetricCard label="Overdue" value={summary.overdue} status={summary.overdue ? "critical" : "healthy"} />
        <MetricCard label="Completed" value={summary.completed} status="healthy" />
        <MetricCard label="Connected boards" value={summary.boards} status="neutral" />
        <MetricCard label={`monday.com status - ${lastChecked}`} value={mondayHealth?.status ?? "unknown"} status={mondayHealth?.status === "healthy" ? "healthy" : "critical"} />
      </div>

      <div className="operations-grid">
        <article className="panel operations-main">
          <div className="operations-toolbar">
            <SearchInput
              placeholder="Search tasks, boards, groups, status..."
              value={query}
              onChange={(event) => setFilter("query", event.target.value)}
              onClear={() => setFilter("query", "")}
            />

            <select value={board} onChange={(event) => setFilter("board", event.target.value)}>
              <option value="all">All boards</option>
              {boardNames.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>

            <select value={status} onChange={(event) => setFilter("status", event.target.value)}>
              <option value="all">All statuses</option>
              {statusNames.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>

            <select
              value={priority}
              onChange={(event) => setFilter("priority", event.target.value)}
            >
              <option value="all">All priorities</option>
              {priorityNames.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>

          <div className="operations-table-wrap">
            <table className="operations-table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Board / Group</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Deadline</th>
                  <th>Assignees</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {filteredTasks.map((task) => (
                  <tr key={task.external_id}>
                    <td>
                      <b>{task.title}</b>
                      {isOverdue(task, now) && (
                        <span className="overdue-label">Overdue</span>
                      )}
                    </td>

                    <td>
                      <b>{task.metadata.board_name ?? "Unknown board"}</b>
                      <span>{task.metadata.group_title ?? "No group"}</span>
                    </td>

                    <td>
                      <StatusBadge status={statusTone(task.status)}>
                        {task.status ?? "Not set"}
                      </StatusBadge>
                    </td>

                    <td>
                      <span className={priorityClass(task.priority)}>
                        {task.priority ?? "Not set"}
                      </span>
                    </td>

                    <td>
                      {task.due_at
                        ? new Date(task.due_at).toLocaleDateString()
                        : "No deadline"}
                    </td>

                    <td>{task.assignee_ids.length || "-"}</td>

                    <td>
                      {task.url && (
                        <a
                          className="operations-open"
                          href={task.url}
                          target="_blank"
                          rel="noreferrer"
                          title="Open in monday.com"
                        >
                          <ExternalLink size={16} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}

                {filteredTasks.length === 0 && (
                  <tr>
                    <td colSpan={7} className="operations-empty">
                      <EmptyState title="No synchronized projects are available.">
                        No tasks match the current filters.
                      </EmptyState>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </article>

        <aside className="operations-side">
          <article className="panel">
            <h2>Boards</h2>
            <button
              className={board === "all" ? "board-filter active" : "board-filter"}
              onClick={() => setFilter("board", "all")}
            >
              <span>All boards</span>
              <b>{tasks.length}</b>
            </button>

            {boardNames.map((name) => {
              const count = tasks.filter(
                (task) => task.metadata.board_name === name,
              ).length;

              return (
                <button
                  key={name}
                  className={board === name ? "board-filter active" : "board-filter"}
                  onClick={() => setFilter("board", name)}
                >
                  <span>{name}</span>
                  <b>{count}</b>
                </button>
              );
            })}
          </article>

          <article className="panel ai-insights-placeholder">
            <span className="eyebrow">COMING NEXT</span>
            <h2>AI Operational Insights</h2>
            <p>
              CTV ONE will identify bottlenecks, deadline risks, workload
              pressure, and projects requiring attention.
            </p>
          </article>

          <article className="panel connector-summary">
            <h2>Connector</h2>
            <div className="status-row">
              <span>monday.com</span>
              <SyncStatus synced={mondayHealth?.status === "healthy"} />
            </div>
            <p className="muted">
              {mondayHealth?.detail ?? "No connector detail available."}
            </p>
          </article>
        </aside>
      </div>
    </PageShell>
  );

  function setFilter(key: keyof OperationsFilters, value: string) {
    setState((current) => ({
      ...current,
      filters: {
        ...current.filters,
        [key]: value,
      },
    }));
  }
}
