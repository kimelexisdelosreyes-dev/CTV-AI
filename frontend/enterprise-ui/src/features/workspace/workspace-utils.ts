import type { StatusTone } from "@/design-system";
import type { WorkspaceActivity, WorkspacePriority, WorkspaceRole } from "./workspace-types";

const urgencyWeight: Record<WorkspacePriority["urgency"], number> = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

export function firstName(name?: string | null): string | null {
  const value = name?.trim();
  if (!value) return null;
  return value.split(/\s+/)[0] ?? null;
}

export function greetingFor(date: Date, displayName?: string | null): string {
  const hour = date.getHours();
  const dayPart = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const name = firstName(displayName);
  return name ? `Good ${dayPart}, ${name}.` : `Good ${dayPart}.`;
}

export function workspaceRole(role?: string | null): WorkspaceRole {
  const value = role?.toLowerCase() ?? "";
  if (value.includes("admin") || value.includes("manager")) return "executive";
  if (value.includes("editor")) return "editor";
  if (value.includes("production")) return "production";
  if (value.includes("technical") || value.includes("it")) return "technical";
  return "general";
}

export function sortPriorities(priorities: WorkspacePriority[], role: WorkspaceRole): WorkspacePriority[] {
  const roleBoost = role === "technical" ? "Enterprise Health" : role === "editor" ? "My AI" : "Projects";
  return [...priorities].sort((a, b) => {
    const urgency = urgencyWeight[a.urgency] - urgencyWeight[b.urgency];
    if (urgency !== 0) return urgency;
    return Number(b.module === roleBoost) - Number(a.module === roleBoost);
  });
}

export function groupActivities(activities: WorkspaceActivity[]) {
  const labels: WorkspaceActivity["group"][] = ["Today", "Yesterday", "Earlier this week"];
  return labels
    .map((label) => ({ label, items: activities.filter((activity) => activity.group === label) }))
    .filter((group) => group.items.length > 0);
}

export function healthTone(status: string): StatusTone {
  const value = status.toLowerCase();
  if (value.includes("healthy") || value.includes("online")) return "healthy";
  if (value.includes("processing") || value.includes("running")) return "processing";
  if (value.includes("warning") || value.includes("degraded") || value.includes("stale")) return "warning";
  if (value.includes("critical") || value.includes("failed")) return "critical";
  if (value.includes("offline") || value.includes("unavailable") || value.includes("disabled")) return "offline";
  return "neutral";
}

export function healthStatusLabel(status: string): "Healthy" | "Processing" | "Warning" | "Critical" | "Offline" {
  const tone = healthTone(status);
  if (tone === "healthy") return "Healthy";
  if (tone === "processing") return "Processing";
  if (tone === "critical") return "Critical";
  if (tone === "offline") return "Offline";
  return "Warning";
}

export function urgencyTone(urgency: WorkspacePriority["urgency"]): StatusTone {
  if (urgency === "critical") return "critical";
  if (urgency === "high") return "warning";
  if (urgency === "low") return "neutral";
  return "processing";
}
