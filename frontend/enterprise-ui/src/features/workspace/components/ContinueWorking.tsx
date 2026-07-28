import { ArrowRight, CheckCircle2 } from "lucide-react";
import { BaseCard, EmptyState, Inline, Metadata, PrimaryButton, ProgressBar, Stack, StatusBadge } from "@/design-system";
import type { WorkspaceContinueItem } from "../workspace-types";

export function ContinueWorking({ item }: { item: WorkspaceContinueItem }) {
  if (item.state === "empty") {
    return (
      <BaseCard title="Continue Working" className="workspace-continue">
        <EmptyState title="No active work is waiting for your attention.">Open Projects to select the next work item.</EmptyState>
      </BaseCard>
    );
  }

  return (
    <BaseCard
      title="Continue Working"
      meta={item.title}
      action={<StatusBadge status={item.state === "completed" ? "healthy" : "processing"}>{item.status}</StatusBadge>}
      className="workspace-continue"
      interactive
      onClick={() => undefined}
      aria-label={`Continue working on ${item.title}`}
    >
      <Stack gap="14px">
        <div>
          <Inline className="workspace-continue__progress-line">
            <strong>{item.progress}% complete</strong>
            <Metadata>{item.dataKind === "demo" ? "Demonstration project context" : "Live and demo context"}</Metadata>
          </Inline>
          <ProgressBar value={item.progress} status="processing" label={`${item.title} progress`} />
        </div>
        <div className="workspace-detail-grid">
          <Metadata><b>Last activity:</b> {item.lastActivity}</Metadata>
          <Metadata><b>Owner:</b> {item.owner}</Metadata>
          <Metadata><b>Related assets:</b> {item.assetCount}</Metadata>
          <Metadata><b>Recent progress:</b> {item.latestOperation}</Metadata>
        </div>
        <Inline className="workspace-recommendation">
          <CheckCircle2 size={18} aria-hidden="true" />
          <span>{item.recommendedAction}</span>
        </Inline>
        <PrimaryButton leadingIcon={<ArrowRight size={16} aria-hidden="true" />}>{item.primaryAction}</PrimaryButton>
      </Stack>
    </BaseCard>
  );
}
