import { CSSProperties, HTMLAttributes, ReactNode } from "react";

function classes(base: string, className?: string): string {
  return className ? `${base} ${className}` : base;
}

export function PageShell({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={classes("ctv-page-shell", className)} {...props}>{children}</section>;
}

export function PageHeader({
  title,
  eyebrow,
  description,
  action,
  className,
}: {
  title: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <header className={classes("ctv-page-header", className)}>
      <div className="ctv-page-header__copy">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        {title}
        {description}
      </div>
      {action}
    </header>
  );
}

export function Section({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={classes("ctv-section", className)} {...props}>{children}</section>;
}

export function Stack({
  children,
  gap,
  className,
}: {
  children: ReactNode;
  gap?: string;
  className?: string;
}) {
  return (
    <div className={classes("ctv-stack", className)} style={{ "--stack-gap": gap } as CSSProperties}>
      {children}
    </div>
  );
}

export function Inline({
  children,
  gap,
  className,
}: {
  children: ReactNode;
  gap?: string;
  className?: string;
}) {
  return (
    <div className={classes("ctv-inline", className)} style={{ "--inline-gap": gap } as CSSProperties}>
      {children}
    </div>
  );
}

export function ResponsiveGrid({
  children,
  min = "220px",
  gap,
  className,
}: {
  children: ReactNode;
  min?: string;
  gap?: string;
  className?: string;
}) {
  return (
    <div
      className={classes("ctv-responsive-grid", className)}
      style={{ "--grid-min": min, "--grid-gap": gap } as CSSProperties}
    >
      {children}
    </div>
  );
}

export function ContentPanel({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  return <article className={classes("ctv-content-panel", className)} {...props}>{children}</article>;
}

