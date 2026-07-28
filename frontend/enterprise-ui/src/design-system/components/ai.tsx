import { ReactNode } from "react";
import { Brain, CheckCircle2, Circle, FileSearch } from "lucide-react";
import { BaseCard } from "./cards";
import { StatusBadge } from "./status";
import { Metadata } from "./typography";
import { StatusTone } from "../tokens";

export function AIThinkingPanel({ steps }: { steps: Array<{ label: string; complete?: boolean }> }) {
  return (
    <BaseCard title={<span className="ctv-inline"><Brain size={18} />Visible AI activity</span>} meta="No private reasoning is shown.">
      {steps.map((step) => <AIProgressStep key={step.label} label={step.label} complete={step.complete} />)}
    </BaseCard>
  );
}

export function AIProgressStep({ label, complete }: { label: string; complete?: boolean }) {
  return <div className="ctv-inline">{complete ? <CheckCircle2 size={16} /> : <Circle size={16} />}<Metadata>{label}</Metadata></div>;
}

export function AIRecommendationCard({ title, recommendation, action }: { title: string; recommendation: string; action?: ReactNode }) {
  return <BaseCard title={title} meta="AI recommendation" action={action}><Metadata>{recommendation}</Metadata></BaseCard>;
}

export function AIConfidenceBadge({ value }: { value: "low" | "medium" | "high" }) {
  const status: StatusTone = value === "high" ? "healthy" : value === "medium" ? "warning" : "critical";
  return <StatusBadge status={status}>Confidence: {value}</StatusBadge>;
}

export function AIJobStatus({ status }: { status: "queued" | "running" | "completed" | "failed" }) {
  const tone: StatusTone = status === "completed" ? "healthy" : status === "failed" ? "critical" : "processing";
  return <StatusBadge status={tone}>AI job {status}</StatusBadge>;
}

export function AISourceReference({ title, source }: { title: string; source: string }) {
  return <BaseCard title={<span className="ctv-inline"><FileSearch size={18} />{title}</span>} meta={source} interactive />;
}

