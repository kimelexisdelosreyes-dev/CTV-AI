import { KnowledgeStats, User } from "@/lib/api";
import { InfrastructureStatusRow } from "@/lib/infrastructure-status";
import {
  HealthCard,
  PageHeader,
  PageShell,
  PageTitle,
  ResponsiveGrid,
  Section,
  StatusBadge,
} from "@/design-system";
import { buildWorkspaceBriefing } from "@/features/workspace/workspace-briefing";
import { DailyBriefing } from "@/features/workspace/components/DailyBriefing";
import { OperationalPulse } from "@/features/workspace/components/OperationalPulse";
import { ContinueWorking } from "@/features/workspace/components/ContinueWorking";
import { TodayPriorities } from "@/features/workspace/components/TodayPriorities";
import { WorkspaceAIActivity } from "@/features/workspace/components/WorkspaceAIActivity";
import { EnterpriseHealthSummary } from "@/features/workspace/components/EnterpriseHealthSummary";

type Props = {
  user: User;
  stats: KnowledgeStats | null;
  infrastructure: InfrastructureStatusRow[] | null;
};

export function Overview({ user, stats, infrastructure }: Props) {
  const briefing = buildWorkspaceBriefing({ user, stats, infrastructure });

  return (
    <PageShell>
      <PageHeader
        eyebrow="CTV ONE WORKSPACE"
        title={<PageTitle>Workspace Intelligence</PageTitle>}
        description={<p className="ctv-body">Daily briefing for current work, priorities, AI activity, and operational health.</p>}
        action={<StatusBadge status="neutral">{briefing.role}</StatusBadge>}
      />

      <DailyBriefing briefing={briefing} />
      <OperationalPulse metrics={briefing.pulse} />

      <ResponsiveGrid min="320px" className="workspace-primary-grid">
        <ContinueWorking item={briefing.continueItem} />
        <TodayPriorities priorities={briefing.priorities} />
      </ResponsiveGrid>

      <ResponsiveGrid min="320px" className="workspace-secondary-grid">
        <WorkspaceAIActivity groups={briefing.activityGroups} />
        <EnterpriseHealthSummary services={briefing.health} />
      </ResponsiveGrid>

      <Section>
        <h2 className="ctv-section-title">Recent Organizational Activity</h2>
        <ResponsiveGrid min="260px">
          {(infrastructure ?? []).slice(0, 3).map((service) => (
            <HealthCard
              detail={`Status: ${service.status}. Category: ${service.category}.`}
              healthy={service.isHealthy}
              key={service.key}
              title={service.label}
            />
          ))}
        </ResponsiveGrid>
      </Section>
    </PageShell>
  );
}
