import { HTMLAttributes, KeyboardEvent, MouseEvent, ReactNode } from "react";
import { CardTitle, Metadata } from "./typography";
import { ProgressBar, StatusBadge } from "./status";
import { StatusTone } from "../tokens";

function classes(base: string, className?: string): string {
  return className ? `${base} ${className}` : base;
}

export function BaseCard({
  children,
  title,
  meta,
  action,
  interactive = false,
  className,
  onClick,
  onKeyDown,
  ...props
}: Omit<HTMLAttributes<HTMLElement>, "title"> & {
  title?: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
  interactive?: boolean;
}) {
  const actionable = Boolean(onClick);

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    onKeyDown?.(event);
    if (event.defaultPrevented || !onClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick(event as unknown as MouseEvent<HTMLElement>);
    }
  }

  return (
    <article
      className={classes("ctv-card", className)}
      data-interactive={interactive ? "true" : "false"}
      {...props}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={actionable ? "button" : props.role}
      tabIndex={actionable ? 0 : props.tabIndex}
    >
      {(title || meta || action) && (
        <div className="ctv-card__header">
          <div>
            {title && <CardTitle>{title}</CardTitle>}
            {meta && <Metadata>{meta}</Metadata>}
          </div>
          {action}
        </div>
      )}
      <div className="ctv-card__body">{children}</div>
    </article>
  );
}

export function MetricCard({ label, value, status }: { label: string; value: ReactNode; status?: StatusTone }) {
  return (
    <BaseCard className="ctv-metric-card">
      <Metadata>{label}</Metadata>
      <strong>{value}</strong>
      {status && <StatusBadge status={status} />}
    </BaseCard>
  );
}

export function ProjectCard({
  name,
  status,
  progress,
  nextAction,
}: {
  name: string;
  status: string;
  progress: number;
  nextAction: string;
}) {
  return (
    <BaseCard title={name} meta={status} interactive>
      <ProgressBar value={progress} status="processing" label={`${name} progress`} />
      <Metadata>{nextAction}</Metadata>
    </BaseCard>
  );
}

export function FileCard({ name, location, status = "neutral" }: { name: string; location: string; status?: StatusTone }) {
  return <BaseCard title={name} meta={location} action={<StatusBadge status={status} />} interactive />;
}

export function KnowledgeCard({ title, source, required = false }: { title: string; source: string; required?: boolean }) {
  return <BaseCard title={title} meta={source} action={<StatusBadge status={required ? "warning" : "healthy"}>{required ? "Required" : "Approved"}</StatusBadge>} interactive />;
}

export function AIInsightCard({ title, insight, action }: { title: string; insight: string; action?: ReactNode }) {
  return <BaseCard title={title} meta="My AI" action={action}><Metadata>{insight}</Metadata></BaseCard>;
}

export function HealthCard({ title, healthy, detail }: { title: string; healthy: boolean; detail: string }) {
  return <BaseCard title={title} action={<StatusBadge status={healthy ? "healthy" : "critical"} /> }><Metadata>{detail}</Metadata></BaseCard>;
}

export function StorageCard({ title, source, online }: { title: string; source: string; online: boolean }) {
  return <BaseCard title={title} meta={source} action={<StatusBadge status={online ? "healthy" : "offline"}>{online ? "Online" : "Offline"}</StatusBadge>} />;
}

export function PersonCard({ name, role, status = "neutral" }: { name: string; role: string; status?: StatusTone }) {
  return <BaseCard title={name} meta={role} action={<StatusBadge status={status} />} />;
}

export function AlertCard({ title, message, status = "warning" }: { title: string; message: string; status?: StatusTone }) {
  return <BaseCard title={title} action={<StatusBadge status={status} />}><Metadata>{message}</Metadata></BaseCard>;
}

export function RecommendationCard({ title, reason }: { title: string; reason: string }) {
  return <BaseCard title={title} meta="Recommended"><Metadata>{reason}</Metadata></BaseCard>;
}
