import { PerformanceEvent } from "@/lib/api";

type Props = {
  events: PerformanceEvent[];
};

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 ms";
  return `${Math.round(value)} ms`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0";
  return Math.round(value).toLocaleString();
}

function formatTime(value: string | null | undefined): string {
  if (!value) return "No timestamp";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export function PerformanceEventsTable({ events }: Props) {
  return (
    <article className="panel">
      <h2>Recent requests</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Intent</th>
              <th>Outcome</th>
              <th>Total</th>
              <th>Ollama</th>
              <th>monday</th>
              <th>Employee</th>
              <th>Tokens</th>
              <th>Chunks</th>
              <th>Tasks</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={`${event.timestamp}-${event.total_endpoint_ms}`}>
                <td>{formatTime(event.timestamp)}</td>
                <td>{event.routed_intent ?? "unknown"}</td>
                <td>{event.outcome ?? "unknown"}</td>
                <td>{formatMs(event.total_endpoint_ms)}</td>
                <td>{formatMs(event.ollama_request_ms)}</td>
                <td>{formatMs(event.monday_operational_context_ms)}</td>
                <td>{formatMs(event.employee_context_ms)}</td>
                <td>{formatNumber(event.estimated_input_token_count)}</td>
                <td>{formatNumber(event.retrieved_chunk_count)}</td>
                <td>{formatNumber(event.operational_task_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
