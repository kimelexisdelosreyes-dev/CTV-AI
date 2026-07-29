import type { CapabilityExecutionResponse } from "../api";
import { CapabilityEmpty } from "./CapabilityEmpty";

const labels: Record<string, string> = { summary: "Summary", action_items: "Action items", follow_ups: "Follow-ups", decisions: "Decisions", key_points: "Key points", recommendations: "Recommendations", answer: "Answer" };
const title = (key: string) => labels[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const asItems = (value: string) => value.split(/\n|(?:^|\s)[•-]\s+/).map((item) => item.trim()).filter(Boolean);

export function CapabilityResult({ result }: { result?: CapabilityExecutionResponse }) {
  if (!result) return <CapabilityEmpty title="No results yet" message="Run a capability to receive a structured enterprise response here." />;
  const entries = Object.entries(result.output);
  return <section className="capability-result" aria-labelledby="capability-result-title"><div className="capability-panel-heading"><div><p className="capability-kicker">Response</p><h2 id="capability-result-title">Result</h2></div><span className="capability-result__status">{result.status}</span></div>{entries.length ? <div className="capability-result__content">{entries.map(([key, value]) => <section key={key}><h3>{title(key)}</h3>{asItems(value).length > 1 ? <ul>{asItems(value).map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ul> : <p>{value}</p>}</section>)}</div> : <p>No structured response was returned.</p>}{result.warnings.length > 0 && <aside className="capability-result__warnings" aria-label="Response notices">{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}</aside>}</section>;
}
