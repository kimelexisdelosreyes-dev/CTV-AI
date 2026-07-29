import type { CapabilitySummary } from "../api";
import { CapabilityEmpty } from "./CapabilityEmpty";
import { CapabilityStatus } from "./CapabilityStatus";

const guidance: Record<string, { latency: string; useCases: string; input: string; output: string; support?: string; documentation?: string }> = {
  company_brain: { latency: "Usually under a minute", useCases: "Finding clear answers from company knowledge", input: "A focused business question", output: "A concise answer and supporting details", support: "Enterprise Intelligence support" },
  hr_policy: { latency: "Usually under a minute", useCases: "Understanding approved HR policies", input: "A policy question", output: "A policy-oriented response", support: "People Operations support" },
  meeting_summary: { latency: "Usually under a minute", useCases: "Capturing decisions, follow-ups, and action items", input: "Meeting notes or transcript text", output: "Summary, actions, follow-ups, and decisions" },
  document_analysis: { latency: "May take a few minutes", useCases: "Reviewing a document for key points and recommendations", input: "Document text", output: "Summary, key points, and recommendations" },
  firefly_prompt_studio: { latency: "Usually under a minute", useCases: "Preparing production-ready creative prompts", input: "A creative brief", output: "Structured prompt guidance" },
  production_planner: { latency: "Usually under a minute", useCases: "Organizing production planning inputs", input: "A production brief", output: "A structured production plan" },
};

export function CapabilityDetail({ item }: { item?: CapabilitySummary }) {
  if (!item) return <CapabilityEmpty title="No capability selected" message="Choose a capability from the catalog to review its purpose, availability, and input guidance." />;
  const details = guidance[item.capability_id] ?? { latency: "Usually under a minute", useCases: "Completing the selected enterprise task", input: "A clear request", output: "A structured capability response" };
  return <section className="capability-detail" aria-labelledby="capability-detail-title"><div className="capability-detail__heading"><div><p className="capability-kicker">{item.category}</p><h2 id="capability-detail-title">{item.name}</h2></div><CapabilityStatus /></div><p className="capability-detail__description">{item.description}</p><dl className="capability-metadata"><div><dt>Lifecycle</dt><dd>Active</dd></div><div><dt>Version</dt><dd>{item.version}</dd></div><div><dt>Availability</dt><dd>Available</dd></div><div><dt>Estimated latency</dt><dd>{details.latency}</dd></div><div><dt>Best use cases</dt><dd>{details.useCases}</dd></div><div><dt>Supported input</dt><dd>{details.input}</dd></div><div><dt>Supported output</dt><dd>{details.output}</dd></div>{details.support && <div><dt>Support</dt><dd>{details.support}</dd></div>}</dl>{details.documentation && <a className="capability-doc-link" href={details.documentation}>View documentation</a>}</section>;
}
