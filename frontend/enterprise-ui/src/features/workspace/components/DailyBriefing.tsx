import { CalendarDays, PlayCircle } from "lucide-react";
import { BaseCard, Inline, Metadata, PageTitle, PrimaryButton, StatusBadge } from "@/design-system";
import type { WorkspaceBriefing } from "../workspace-types";

export function DailyBriefing({ briefing }: { briefing: WorkspaceBriefing }) {
  return (
    <BaseCard className="workspace-briefing" aria-labelledby="workspace-briefing-title">
      <div className="workspace-briefing__copy">
        <Inline gap="10px">
          <CalendarDays size={16} aria-hidden="true" />
          <Metadata>{briefing.dateLabel}</Metadata>
          <StatusBadge status={briefing.dataKind === "demo" ? "warning" : "processing"}>
            {briefing.dataKind === "demo" ? "Demonstration data" : "Live and demo context"}
          </StatusBadge>
        </Inline>
        <PageTitle id="workspace-briefing-title">{briefing.greeting}</PageTitle>
        <p className="ctv-body">{briefing.summary}</p>
      </div>
      <PrimaryButton leadingIcon={<PlayCircle size={16} aria-hidden="true" />}>{briefing.primaryAction}</PrimaryButton>
    </BaseCard>
  );
}
