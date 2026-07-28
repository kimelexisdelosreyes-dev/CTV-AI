import { CSSProperties, ReactNode } from "react";
import { StatusTone, statusTokens } from "../tokens";

const labels: Record<StatusTone, string> = {
  healthy: "Healthy",
  processing: "Processing",
  warning: "Warning",
  critical: "Critical",
  offline: "Offline",
  neutral: "Neutral",
};

export function StatusBadge({
  status = "neutral",
  children,
}: {
  status?: StatusTone;
  children?: ReactNode;
}) {
  return <span className={`ctv-status ctv-status--${status}`}><StatusDot status={status} />{children ?? labels[status]}</span>;
}

export function StatusDot({ status = "neutral" }: { status?: StatusTone }) {
  return <span className={`ctv-status-dot ctv-status--${status}`} aria-hidden="true" />;
}

export function ProgressBar({
  value,
  status = "processing",
  label,
}: {
  value: number;
  status?: StatusTone;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div aria-label={label ?? `Progress ${clamped}%`} role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100} className="ctv-progress">
      <span className="ctv-progress__bar" style={{ "--progress-value": `${clamped}%`, "--progress-color": statusTokens[status] } as CSSProperties} />
    </div>
  );
}

export function ProgressRing({ value, status = "processing" }: { value: number; status?: StatusTone }) {
  const clamped = Math.max(0, Math.min(100, value));
  return <span className="ctv-progress-ring" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100} style={{ "--ring-value": `${clamped}%`, "--ring-color": statusTokens[status] } as CSSProperties}>{clamped}%</span>;
}

export function HealthIndicator({ healthy, label }: { healthy: boolean; label: string }) {
  return <StatusBadge status={healthy ? "healthy" : "critical"}>{label}</StatusBadge>;
}

export function SyncStatus({ synced }: { synced: boolean }) {
  return <StatusBadge status={synced ? "healthy" : "warning"}>{synced ? "Synced" : "Sync needed"}</StatusBadge>;
}

export function OnlineStatus({ online }: { online: boolean }) {
  return <StatusBadge status={online ? "healthy" : "offline"}>{online ? "Online" : "Offline"}</StatusBadge>;
}

