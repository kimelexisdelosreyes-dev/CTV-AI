import { Activity } from "lucide-react";
import { Inline, Metadata, StatusBadge } from "@/design-system";
import type { WorkspacePulseMetric } from "../workspace-types";

export function OperationalPulse({ metrics }: { metrics: WorkspacePulseMetric[] }) {
  return (
    <section className="workspace-pulse" aria-labelledby="workspace-pulse-title">
      <Inline>
        <Activity size={17} aria-hidden="true" />
        <h2 className="ctv-section-title" id="workspace-pulse-title">Operational Pulse</h2>
      </Inline>
      <div className="workspace-pulse__strip">
        {metrics.map((metric) => (
          <div className="workspace-pulse__metric" key={metric.label}>
            <span className="ctv-caption">{metric.label}</span>
            <strong aria-label={`${metric.label}: ${metric.value}`}>{metric.value}</strong>
            <Metadata>{metric.detail}</Metadata>
            <StatusBadge status={metric.status}>{metric.dataKind === "demo" ? "Demo" : metric.status}</StatusBadge>
          </div>
        ))}
      </div>
    </section>
  );
}
