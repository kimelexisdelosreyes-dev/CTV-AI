import { ArrowRight, Flag } from "lucide-react";
import { BaseCard, EmptyState, Inline, Metadata, SecondaryButton, Stack, StatusBadge } from "@/design-system";
import type { WorkspacePriority } from "../workspace-types";
import { urgencyTone } from "../workspace-utils";

export function TodayPriorities({ priorities }: { priorities: WorkspacePriority[] }) {
  return (
    <BaseCard title="Today's Priorities" meta="Actionable operational focus" className="workspace-priorities">
      {priorities.length === 0 ? (
        <EmptyState title="No urgent priorities require attention.">Workspace will surface new actions when live data changes.</EmptyState>
      ) : (
        <Stack gap="12px">
          {priorities.map((priority) => (
            <article className="workspace-priority" key={priority.id} tabIndex={0} aria-label={`${priority.urgency} priority: ${priority.title}`}>
              <Inline className="workspace-priority__header">
                <Flag size={16} aria-hidden="true" />
                <strong>{priority.title}</strong>
                <StatusBadge status={urgencyTone(priority.urgency)}>{priority.urgency}</StatusBadge>
              </Inline>
              <Metadata>{priority.category} / {priority.module}</Metadata>
              <p className="ctv-body">{priority.explanation}</p>
              <SecondaryButton size="small" leadingIcon={<ArrowRight size={14} aria-hidden="true" />}>{priority.action}</SecondaryButton>
            </article>
          ))}
        </Stack>
      )}
    </BaseCard>
  );
}
