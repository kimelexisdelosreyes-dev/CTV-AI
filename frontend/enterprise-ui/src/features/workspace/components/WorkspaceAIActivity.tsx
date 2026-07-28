import { Bot, ExternalLink } from "lucide-react";
import { BaseCard, EmptyState, Inline, Metadata, StaggerGroup, StatusBadge } from "@/design-system";
import type { WorkspaceActivity } from "../workspace-types";

const statusTone = {
  running: "processing",
  completed: "healthy",
  warning: "warning",
  failed: "critical",
  cancelled: "offline",
} as const;

export function WorkspaceAIActivity({ groups }: { groups: Array<{ label: WorkspaceActivity["group"]; items: WorkspaceActivity[] }> }) {
  return (
    <BaseCard title="AI Activity" meta="Operational timeline" className="workspace-activity">
      {groups.length === 0 ? (
        <EmptyState title="No recent AI activity is available.">AI activity will appear here after jobs run.</EmptyState>
      ) : (
        <StaggerGroup>
          {groups.map((group) => (
            <section className="workspace-activity-group" key={group.label} aria-label={group.label}>
              <h3 className="ctv-card-title">{group.label}</h3>
              {group.items.map((item) => (
                <article className="workspace-activity-item" key={item.id} tabIndex={0}>
                  <Inline>
                    <Bot size={16} aria-hidden="true" />
                    <strong>{item.action}</strong>
                    <StatusBadge status={statusTone[item.status]}>{item.status}</StatusBadge>
                  </Inline>
                  <Metadata>{item.object} / {item.relativeTime} / {item.sourceType}</Metadata>
                  {item.destination && <Metadata><ExternalLink size={13} aria-hidden="true" /> {item.destination}</Metadata>}
                </article>
              ))}
            </section>
          ))}
        </StaggerGroup>
      )}
    </BaseCard>
  );
}
