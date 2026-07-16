import { PerformanceSummary } from "@/lib/api";

type Props = {
  summary: PerformanceSummary;
};

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 ms";
  return `${Math.round(value)} ms`;
}

function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 tok/s";
  return `${value.toFixed(1)} tok/s`;
}

export function PerformanceSummaryCards({ summary }: Props) {
  return (
    <div className="metric-grid developer-metrics">
      <article className="metric-card">
        <span>Average total time</span>
        <strong>{formatMs(summary.average_total_duration_ms)}</strong>
      </article>
      <article className="metric-card">
        <span>Median total time</span>
        <strong>{formatMs(summary.median_total_duration_ms)}</strong>
      </article>
      <article className="metric-card">
        <span>P95 total time</span>
        <strong>{formatMs(summary.p95_total_duration_ms)}</strong>
      </article>
      <article className="metric-card">
        <span>Total measured requests</span>
        <strong>{summary.request_count}</strong>
      </article>
      <article className="metric-card">
        <span>Average Ollama time</span>
        <strong>{formatMs(summary.average_ollama_duration_ms)}</strong>
      </article>
      <article className="metric-card">
        <span>Average monday time</span>
        <strong>{formatMs(summary.average_monday_duration_ms)}</strong>
      </article>
      <article className="metric-card">
        <span>Average employee-context time</span>
        <strong>{formatMs(summary.average_employee_context_duration_ms)}</strong>
      </article>
      <article className="metric-card">
        <span>Average tokens per second</span>
        <strong>{formatRate(summary.average_tokens_per_second)}</strong>
      </article>
    </div>
  );
}
