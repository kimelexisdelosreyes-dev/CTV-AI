"use client";

import {
  Dispatch,
  SetStateAction,
  useCallback,
  useEffect,
  useMemo,
} from "react";
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Search,
  ServerCog,
  Workflow,
} from "lucide-react";

import {
  apiFetch,
  ConnectorHealth,
  ConnectorProject,
  ConnectorTask,
} from "@/lib/api";
import {
  OperationsFilters,
  OperationsState,
  operationsSnapshotIsStale,
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

function statusClass(status: string | null): string {
  const value = (status ?? "").toLowerCase();

  if (value.includes("done") || value.includes("complete")) {
    return "status-chip status-done";
  }
  if (value.includes("stuck") || value.includes("blocked")) {
    return "status-chip status-stuck";
  }
  if (value.includes("working") || value.includes("progress")) {
    return "status-chip status-working";
  }
  return "status-chip status-neutral";
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

  const load = useCallback(async (mode: "initial" | "background" | "manual") => {
    if (state.loading || state.refreshing) return;

    const hasSnapshot = state.lastUpdated !== null;
    setState((current) => ({
      ...current,
      loading: mode === "initial" && !hasSnapshot,
      refreshing: mode !== "initial" || hasSnapshot,
      error: "",
    }));

    try {
      const [healthData, projectData, taskData] = await Promise.all([
        apiFetch<ConnectorHealth[]>("/connectors/health"),
        apiFetch<ConnectorProject[]>("/connectors/monday/projects"),
        apiFetch<ConnectorTask[]>("/connectors/monday/tasks"),
      ]);

      setState((current) => ({
        ...current,
        health: healthData,
        projects: projectData,
        tasks: taskData,
        loading: false,
        refreshing: false,
        error: "",
        lastUpdated: new Date().toISOString(),
      }));
    } catch (cause) {
      setState((current) => ({
        ...current,
        loading: false,
        refreshing: false,
        error:
          cause instanceof Error
            ? cause.message
            : "Could not load monday.com operations data.",
      }));
    }
  }, [setState, state.lastUpdated, state.loading, state.refreshing]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!state.lastUpdated) {
        void load("initial");
      } else if (operationsSnapshotIsStale(state.lastUpdated, Date.now())) {
        void load("background");
      }
    }, 0);
    return () => window.clearTimeout(handle);
  }, [load, state.lastUpdated]);

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
    return <section className="panel">Loading Operations Workspace...</section>;
  }

  return (
    <section>
      <div className="page-heading operations-heading">
        <div>
          <span className="eyebrow">ENTERPRISE OPERATIONS</span>
          <h1>Operations Workspace</h1>
          <p>
            {updatedLabel}
            {refreshing ? " - Refreshing..." : ""}
          </p>
        </div>

        <button
          className="operations-refresh"
          onClick={() => load("manual")}
          disabled={refreshing}
        >
          <RefreshCw size={16} className={refreshing ? "spin" : ""} />
          {refreshing ? "Refreshing..." : "Refresh monday"}
        </button>
      </div>

      {error && (
        <article className="panel operations-error">
          <AlertTriangle size={18} />
          <div>
            <b>Operations refresh failed</b>
            <p>{error}</p>
            {lastUpdated && (
              <p>Showing data from {new Date(lastUpdated).toLocaleString()}.</p>
            )}
          </div>
        </article>
      )}

      <div className="metric-grid operations-metrics">
        <article className="metric-card">
          <Workflow size={18} />
          <span>Active tasks</span>
          <strong>{summary.active}</strong>
        </article>

        <article className="metric-card">
          <CalendarClock size={18} />
          <span>Due today</span>
          <strong>{summary.dueToday}</strong>
        </article>

        <article className="metric-card">
          <AlertTriangle size={18} />
          <span>Overdue</span>
          <strong>{summary.overdue}</strong>
        </article>

        <article className="metric-card">
          <CheckCircle2 size={18} />
          <span>Completed</span>
          <strong>{summary.completed}</strong>
        </article>

        <article className="metric-card">
          <ServerCog size={18} />
          <span>Connected boards</span>
          <strong>{summary.boards}</strong>
        </article>

        <article className="metric-card connector-metric">
          <span>monday.com status</span>
          <strong className={mondayHealth?.status === "healthy" ? "good" : "bad"}>
            {mondayHealth?.status ?? "unknown"}
          </strong>
          <small>{lastChecked}</small>
        </article>
      </div>

      <div className="operations-grid">
        <article className="panel operations-main">
          <div className="operations-toolbar">
            <div className="operations-search">
              <Search size={16} />
              <input
                placeholder="Search tasks, boards, groups, status..."
                value={query}
                onChange={(event) => setFilter("query", event.target.value)}
              />
            </div>

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
                      <span className={statusClass(task.status)}>
                        {task.status ?? "Not set"}
                      </span>
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
                      No tasks match the current filters.
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
              <b className={mondayHealth?.status === "healthy" ? "good" : "bad"}>
                {mondayHealth?.status ?? "unknown"}
              </b>
            </div>
            <p className="muted">
              {mondayHealth?.detail ?? "No connector detail available."}
            </p>
          </article>
        </aside>
      </div>
    </section>
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
