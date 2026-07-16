"use client";

import { useMemo } from "react";
import { Activity, Cpu, Gauge } from "lucide-react";

import { PerformanceEventsTable } from "@/components/performance-events-table";
import { PerformanceSummaryCards } from "@/components/performance-summary-cards";
import {
  DeveloperStatus,
  PerformanceEvent,
  PerformanceSummary,
} from "@/lib/api";

type Props = {
  developerStatus: DeveloperStatus | null;
  events: PerformanceEvent[];
  error: string;
  loading: boolean;
  summary: PerformanceSummary | null;
};

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 ms";
  return `${Math.round(value)} ms`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0";
  return Math.round(value).toLocaleString();
}

function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 tok/s";
  return `${value.toFixed(1)} tok/s`;
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Pending";
  return `${value.toFixed(1)}%`;
}

export function PerformanceDashboard({
  developerStatus,
  events,
  error,
  loading,
  summary,
}: Props) {
  const latest = events[0] ?? null;

  const stageBreakdown = useMemo(() => {
    if (!latest) return [];
    return [
      ["Router", latest.intelligence_router_ms],
      ["Employee", latest.employee_context_ms],
      ["monday.com", latest.monday_operational_context_ms],
      ["Embedding", latest.embedding_ms],
      ["Qdrant", latest.qdrant_vector_search_ms],
      ["Prompt", latest.prompt_assembly_ms],
      ["Ollama", latest.ollama_request_ms],
    ] as const;
  }, [latest]);

  const largestStage = Math.max(
    1,
    ...stageBreakdown.map(([, value]) => value ?? 0),
  );

  return (
    <>
      {loading && (
        <article className="developer-state">
          <Gauge size={18} />
          <p>Loading performance metrics.</p>
        </article>
      )}

      {!loading && error && !developerStatus?.enabled && (
        <article className="developer-state developer-error">
          <Cpu size={18} />
          <p>{error}</p>
        </article>
      )}

      {!loading && error && developerStatus?.enabled && (
        <article className="developer-state developer-error">
          <Cpu size={18} />
          <p>{error}</p>
        </article>
      )}

      {!loading && developerStatus?.enabled && !error && !latest && (
        <article className="developer-state">
          <Activity size={18} />
          <p>No AI performance events have been captured yet.</p>
        </article>
      )}

      {!loading && developerStatus?.enabled && !error && latest && (
        <>
          <div className="metric-grid developer-metrics">
            <article className="metric-card">
              <span>Latest total time</span>
              <strong>{formatMs(latest.total_endpoint_ms)}</strong>
            </article>
            <article className="metric-card">
              <span>Routed intent</span>
              <strong>{latest.routed_intent ?? "unknown"}</strong>
            </article>
            <article className="metric-card">
              <span>Routing confidence</span>
              <strong>{latest.routing_confidence?.toFixed(2) ?? "0.00"}</strong>
            </article>
            <article className="metric-card">
              <span>Outcome</span>
              <strong>{latest.outcome ?? "unknown"}</strong>
            </article>
          </div>

          <div className="metric-grid developer-metrics">
            <article className="metric-card">
              <span>Estimated input tokens</span>
              <strong>{formatNumber(latest.estimated_input_token_count)}</strong>
            </article>
            <article className="metric-card">
              <span>Estimated output tokens</span>
              <strong>{formatNumber(latest.estimated_output_token_count)}</strong>
            </article>
            <article className="metric-card">
              <span>Tokens per second</span>
              <strong>{formatRate(latest.tokens_per_second)}</strong>
            </article>
            <article className="metric-card">
              <span>Current model</span>
              <strong>{latest.model_name ?? "unknown"}</strong>
            </article>
          </div>

          <div className="two-column">
            <article className="panel">
              <h2>Latest stage breakdown</h2>
              <div className="developer-bars">
                {stageBreakdown.map(([label, value]) => (
                  <div className="developer-bar-row" key={label}>
                    <span>{label}</span>
                    <div>
                      <i
                        style={{
                          width: `${Math.max(
                            4,
                            ((value ?? 0) / largestStage) * 100,
                          )}%`,
                        }}
                      />
                    </div>
                    <b>{formatMs(value)}</b>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <h2>Latest request metadata</h2>
              <div className="status-row">
                <span>Prompt size</span>
                <b>{formatNumber(latest.prompt_size)} chars</b>
              </div>
              <div className="status-row">
                <span>Retrieved chunks</span>
                <b>{formatNumber(latest.retrieved_chunk_count)}</b>
              </div>
              <div className="status-row">
                <span>Operational tasks</span>
                <b>{formatNumber(latest.operational_task_count)}</b>
              </div>
              <div className="status-row">
                <span>GPU utilization</span>
                <b>{formatPercent(latest.gpu_utilization)}</b>
              </div>
              <div className="status-row">
                <span>CPU utilization</span>
                <b>{formatPercent(latest.cpu_utilization)}</b>
              </div>
            </article>
          </div>

          {summary && <PerformanceSummaryCards summary={summary} />}

          <PerformanceEventsTable events={events} />
        </>
      )}
    </>
  );
}
