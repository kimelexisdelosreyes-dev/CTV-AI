import { DeveloperConsole } from "@/components/developer-console";
import { EnterpriseMap } from "@/components/enterprise-map";
import {
  AIServiceNode,
  EmptyState,
  InlineAlert,
  PageHeader,
  PageShell,
  PageTitle,
  ResponsiveGrid,
  SystemHealthSummary,
} from "@/design-system";
import { User } from "@/lib/api";
import { InfrastructureStatusRow } from "@/lib/infrastructure-status";

type Props = {
  data: InfrastructureStatusRow[] | null;
  user: User;
};

export function Infrastructure({ data, user }: Props) {
  const healthy = Boolean(data?.every((service) => service.isHealthy));

  return (
    <PageShell>
      <PageHeader
        eyebrow="ENTERPRISE CONTROL CENTER"
        title={<PageTitle>Enterprise Control Center</PageTitle>}
        description={<p className="ctv-body">Enterprise Health for platform services, storage readiness, AI activity, and integrations.</p>}
      />

      <SystemHealthSummary
        healthy={healthy}
        detail={healthy ? "No enterprise alerts require attention." : "One or more Enterprise Infrastructure services need attention."}
      />

      <ResponsiveGrid min="240px">
        {(data ?? []).map((service) => (
          <AIServiceNode
            key={service.key}
            status={service.isHealthy ? "healthy" : "critical"}
            title={service.label}
          >
            <p className="ctv-metadata">Status: {service.status}</p>
            <p className="ctv-metadata">Category: {service.category}</p>
            {user.role === "admin" && (
              <p className="ctv-metadata">Technical detail: {service.model}</p>
            )}
          </AIServiceNode>
        ))}
      </ResponsiveGrid>

      {!data?.length && (
        <EmptyState title="No enterprise alerts require attention.">
          System status data is unavailable. Workspace and Knowledge Center
          remain available while Enterprise Health refreshes.
        </EmptyState>
      )}

      {!healthy && data?.length ? (
        <InlineAlert title="Enterprise Health degraded" status="warning">
          A service is reporting a non-healthy status. Unaffected modules remain
          available.
        </InlineAlert>
      ) : null}

      <section className="ctv-section">
        <h2 className="ctv-section-title">Enterprise Map</h2>
        <EnterpriseMap />
      </section>

      {user.role === "admin" && <DeveloperConsole />}
    </PageShell>
  );
}
