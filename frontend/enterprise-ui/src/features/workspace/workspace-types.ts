import type { StatusTone } from "@/design-system";

export type WorkspaceRole = "executive" | "editor" | "production" | "technical" | "general";

export type WorkspaceDataKind = "live" | "demo" | "mixed" | "unavailable";

export type WorkspacePulseMetric = {
  label: string;
  value: string;
  detail: string;
  status: StatusTone;
  dataKind: WorkspaceDataKind;
};

export type WorkspacePriority = {
  id: string;
  title: string;
  category: string;
  urgency: "critical" | "high" | "normal" | "low";
  explanation: string;
  module: string;
  action: string;
};

export type WorkspaceActivity = {
  id: string;
  action: string;
  object: string;
  relativeTime: string;
  group: "Today" | "Yesterday" | "Earlier this week";
  status: "running" | "completed" | "warning" | "failed" | "cancelled";
  sourceType: string;
  destination?: string;
};

export type WorkspaceHealthService = {
  id: string;
  name: string;
  status: "Healthy" | "Processing" | "Warning" | "Critical" | "Offline";
  tone: StatusTone;
  detail: string;
  lastChecked: string;
  action?: string;
  dataKind: WorkspaceDataKind;
};

export type WorkspaceContinueItem = {
  title: string;
  status: string;
  progress: number;
  lastActivity: string;
  owner: string;
  assetCount: number;
  latestOperation: string;
  recommendedAction: string;
  primaryAction: string;
  state: "active" | "empty" | "unavailable" | "completed" | "loading";
  dataKind: WorkspaceDataKind;
};

export type WorkspaceBriefing = {
  greeting: string;
  dateLabel: string;
  summary: string;
  primaryAction: string;
  role: WorkspaceRole;
  dataKind: WorkspaceDataKind;
  pulse: WorkspacePulseMetric[];
  continueItem: WorkspaceContinueItem;
  priorities: WorkspacePriority[];
  activityGroups: Array<{ label: WorkspaceActivity["group"]; items: WorkspaceActivity[] }>;
  health: WorkspaceHealthService[];
};
