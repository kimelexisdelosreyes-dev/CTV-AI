import type { KnowledgeStats, User } from "@/lib/api";
import type { InfrastructureStatusRow } from "@/lib/infrastructure-status";
import type { WorkspaceActivity, WorkspaceBriefing, WorkspacePriority } from "./workspace-types";
import { greetingFor, groupActivities, healthStatusLabel, healthTone, sortPriorities, workspaceRole } from "./workspace-utils";

const demoActivities: WorkspaceActivity[] = [
  { id: "ocr-fire", action: "OCR completed", object: "FireStation_Archive_1978.tif", relativeTime: "12 minutes ago", group: "Today", status: "completed", sourceType: "Enterprise Files", destination: "Files" },
  { id: "summary-lee", action: "Transcript summary prepared", object: "Interview_Lee_1987.mov", relativeTime: "34 minutes ago", group: "Today", status: "completed", sourceType: "Knowledge Center", destination: "Knowledge" },
  { id: "related-interviews", action: "Three related interviews were found", object: "Caloocan Fire Documentary", relativeTime: "Yesterday", group: "Yesterday", status: "completed", sourceType: "My AI", destination: "Projects" },
  { id: "nas-storage", action: "Storage warning detected", object: "CTV-NAS-01", relativeTime: "Monday", group: "Earlier this week", status: "warning", sourceType: "Enterprise Health", destination: "Infrastructure" },
];

const demoPriorities: WorkspacePriority[] = [
  { id: "review-fire", title: "Review Fire Documentary interview summary", category: "Approval", urgency: "high", explanation: "The latest transcript summary is ready for executive review.", module: "Projects", action: "Continue project" },
  { id: "storage-warning", title: "Check NAS storage warning", category: "Infrastructure", urgency: "high", explanation: "CTV-NAS-01 is near capacity in the demo health model.", module: "Enterprise Health", action: "Open Control Center" },
  { id: "archive-output", title: "Approve archive restoration output", category: "Files", urgency: "normal", explanation: "OCR and archive discovery completed for the documentary source.", module: "Files", action: "Review asset" },
  { id: "monday-sync", title: "Confirm Monday.com synchronization", category: "Operations", urgency: "low", explanation: "The demo operations sync completed and can be reviewed if needed.", module: "Operations", action: "Review operations" },
];

export function buildWorkspaceBriefing({
  user,
  stats,
  infrastructure,
  now = new Date(),
}: {
  user: User;
  stats: KnowledgeStats | null;
  infrastructure: InfrastructureStatusRow[] | null;
  now?: Date;
}): WorkspaceBriefing {
  const role = workspaceRole(user.role);
  const activeSources = stats?.ready_documents ?? 0;
  const failedSources = stats?.failed_documents ?? 0;
  const processingSources = stats?.processing_documents ?? 0;
  const infraRows = infrastructure ?? [];
  const unhealthy = infraRows.filter((service) => !service.isHealthy);
  const hasLiveStats = Boolean(stats);
  const hasHealth = infraRows.length > 0;
  const dataKind = hasLiveStats || hasHealth ? "mixed" : "demo";

  const priorities = sortPriorities(
    [
      ...demoPriorities,
      ...(failedSources > 0
        ? [{ id: "failed-sources", title: "Review failed Knowledge Center sources", category: "Knowledge", urgency: "critical" as const, explanation: `${failedSources} source${failedSources === 1 ? "" : "s"} need attention before retrieval is complete.`, module: "Knowledge Center", action: "Open Knowledge Center" }]
        : []),
      ...(unhealthy.length
        ? [{ id: "health-warning", title: "Review enterprise service warning", category: "Infrastructure", urgency: "high" as const, explanation: `${unhealthy[0].label} is reporting ${unhealthy[0].status}.`, module: "Enterprise Health", action: "Open Control Center" }]
        : []),
    ],
    role,
  ).slice(0, 5);

  return {
    greeting: greetingFor(now, user.full_name),
    dateLabel: new Intl.DateTimeFormat("en", { weekday: "long", month: "long", day: "numeric" }).format(now),
    summary: `Here is what requires your attention today: ${priorities.length} priorities, ${activeSources} ready sources, and ${unhealthy.length} service warning${unhealthy.length === 1 ? "" : "s"}.`,
    primaryAction: "Review priorities",
    role,
    dataKind,
    pulse: [
      { label: "Ready sources", value: String(activeSources), detail: hasLiveStats ? "Current Knowledge Center" : "No live stats", status: "healthy", dataKind: hasLiveStats ? "live" : "unavailable" },
      { label: "Processing", value: String(processingSources), detail: hasLiveStats ? "Current Knowledge Center" : "No live stats", status: processingSources ? "processing" : "neutral", dataKind: hasLiveStats ? "live" : "unavailable" },
      { label: "AI jobs completed", value: "3", detail: "Demonstration data", status: "healthy", dataKind: "demo" },
      { label: "Storage alerts", value: String(unhealthy.length || 1), detail: unhealthy.length ? "Current infrastructure" : "Demonstration data", status: unhealthy.length ? "warning" : "warning", dataKind: unhealthy.length ? "live" : "demo" },
      { label: "Synchronization", value: "Current", detail: "Demonstration data", status: "healthy", dataKind: "demo" },
    ],
    continueItem: {
      title: "Caloocan Fire Documentary",
      status: "Executive review",
      progress: 84,
      lastActivity: "Transcript indexed yesterday",
      owner: role === "technical" ? "Infrastructure and Production" : "Production Team",
      assetCount: activeSources || 17,
      latestOperation: "OCR completed and related archive discovered",
      recommendedAction: "Review the latest interview summary",
      primaryAction: "Continue project",
      state: "active",
      dataKind: hasLiveStats ? "mixed" : "demo",
    },
    priorities,
    activityGroups: groupActivities(demoActivities),
    health: [
      ...infraRows.map((service) => ({
        id: service.key,
        name: service.label,
        status: healthStatusLabel(service.status),
        tone: healthTone(service.status),
        detail: service.isHealthy ? "Responding normally" : `Status: ${service.status}. Category: ${service.category}.`,
        lastChecked: "Current API response",
        action: service.isHealthy ? undefined : "Review service",
        dataKind: "live" as const,
      })),
      { id: "monday", name: "Monday.com", status: "Healthy", tone: "healthy", detail: "Last synchronized 12 minutes ago", lastChecked: "Demonstration data", dataKind: "demo" as const },
      { id: "search", name: "Enterprise Search", status: "Healthy", tone: "healthy", detail: "Indexes available for Workspace discovery", lastChecked: "Demonstration data", dataKind: "demo" as const },
      { id: "storage", name: "Storage", status: unhealthy.length ? "Warning" : "Warning", tone: "warning", detail: unhealthy.length ? "One service needs attention" : "NAS usage at 91%", lastChecked: unhealthy.length ? "Current infrastructure" : "Demonstration data", action: "Open Control Center", dataKind: unhealthy.length ? "mixed" : "demo" as const },
    ],
  };
}
