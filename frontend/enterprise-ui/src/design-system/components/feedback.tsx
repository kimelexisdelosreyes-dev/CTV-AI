import { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { StatusTone } from "../tokens";
import { CardTitle, Metadata } from "./typography";
import { Button, SecondaryButton } from "./buttons";

const icons = {
  healthy: CheckCircle2,
  processing: Info,
  warning: AlertTriangle,
  critical: XCircle,
  offline: AlertTriangle,
  neutral: Info,
};

export function InlineAlert({ status = "neutral", title, children }: { status?: StatusTone; title: string; children: ReactNode }) {
  const Icon = icons[status];
  return (
    <div className={`ctv-alert ctv-status--${status}`} role={status === "critical" ? "alert" : "status"}>
      <div className="ctv-inline"><Icon size={18} /><CardTitle>{title}</CardTitle></div>
      <Metadata>{children}</Metadata>
    </div>
  );
}

export function Banner(props: { status?: StatusTone; title: string; children: ReactNode }) {
  return <InlineAlert {...props} />;
}

export function Toast({ title, children }: { title: string; children: ReactNode }) {
  return <div className="ctv-toast"><InlineAlert title={title} status="healthy">{children}</InlineAlert></div>;
}

export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return <div className="ctv-stack" aria-hidden="true">{Array.from({ length: lines }, (_, index) => <span className="ctv-skeleton" key={index} style={{ width: `${100 - index * 14}%` }} />)}</div>;
}

export function EmptyState({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <div className="ctv-empty-state"><CardTitle>{title}</CardTitle><Metadata>{children}</Metadata>{action}</div>;
}

export function ErrorState({ title, children, onRetry }: { title: string; children: ReactNode; onRetry?: () => void }) {
  return <div className="ctv-error-state" role="alert"><CardTitle>{title}</CardTitle><Metadata>{children}</Metadata>{onRetry && <SecondaryButton onClick={onRetry}>Retry</SecondaryButton>}</div>;
}

export function ConfirmationDialog({
  title,
  children,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
}: {
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
}) {
  return (
    <div className="ctv-card" role="dialog" aria-modal="true" aria-labelledby="ctv-confirm-title">
      <CardTitle id="ctv-confirm-title">{title}</CardTitle>
      <Metadata>{children}</Metadata>
      <div className="ctv-inline">
        <SecondaryButton>{cancelLabel}</SecondaryButton>
        <Button variant="danger">{confirmLabel}</Button>
      </div>
    </div>
  );
}

