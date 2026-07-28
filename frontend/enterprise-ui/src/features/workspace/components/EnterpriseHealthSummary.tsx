import { ShieldCheck } from "lucide-react";
import { BaseCard, EmptyState, Inline, Metadata, SecondaryButton, Stack, StatusBadge } from "@/design-system";
import type { WorkspaceHealthService } from "../workspace-types";

export function EnterpriseHealthSummary({ services }: { services: WorkspaceHealthService[] }) {
  return (
    <BaseCard title="Enterprise Health" meta="Concise service summary" className="workspace-health">
      {services.length === 0 ? (
        <EmptyState title="Enterprise health is unavailable.">Workspace remains available while health data refreshes.</EmptyState>
      ) : (
        <Stack gap="12px">
          {services.map((service) => (
            <article className="workspace-health-row" key={service.id} tabIndex={0}>
              <Inline>
                <ShieldCheck size={16} aria-hidden="true" />
                <strong>{service.name}</strong>
                <StatusBadge status={service.tone}>{service.status}</StatusBadge>
              </Inline>
              <Metadata>{service.detail}</Metadata>
              <Metadata>{service.lastChecked}{service.dataKind === "demo" ? " / Demonstration data" : ""}</Metadata>
              {service.action && <SecondaryButton size="small">{service.action}</SecondaryButton>}
            </article>
          ))}
          <SecondaryButton>Open Enterprise Control Center</SecondaryButton>
        </Stack>
      )}
    </BaseCard>
  );
}
