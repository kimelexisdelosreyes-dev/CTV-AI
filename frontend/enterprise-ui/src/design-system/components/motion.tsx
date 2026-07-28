import { CSSProperties, HTMLAttributes, ReactNode } from "react";

type MotionName =
  | "fade"
  | "slide-up"
  | "slide-down"
  | "slide-left"
  | "slide-right"
  | "scale"
  | "highlight"
  | "route";

const motionClasses: Record<MotionName, string> = {
  fade: "ctv-fade-in",
  "slide-up": "ctv-slide-in-up",
  "slide-down": "ctv-slide-in-down",
  "slide-left": "ctv-slide-in-left",
  "slide-right": "ctv-slide-in-right",
  scale: "ctv-scale-subtle",
  highlight: "ctv-highlight",
  route: "ctv-route-transition",
};

function classes(base: string, className?: string): string {
  return className ? `${base} ${className}` : base;
}

export function MotionSurface({
  children,
  motion = "fade",
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  motion?: MotionName;
}) {
  return (
    <div className={classes(`ctv-motion-surface ${motionClasses[motion]}`, className)} {...props}>
      {children}
    </div>
  );
}

export function FadeIn(props: Omit<Parameters<typeof MotionSurface>[0], "motion">) {
  return <MotionSurface motion="fade" {...props} />;
}

export function SlideIn({ direction = "up", ...props }: Omit<Parameters<typeof MotionSurface>[0], "motion"> & { direction?: "up" | "down" | "left" | "right" }) {
  return <MotionSurface motion={`slide-${direction}` as MotionName} {...props} />;
}

export function RouteTransition(props: Omit<Parameters<typeof MotionSurface>[0], "motion">) {
  return <MotionSurface motion="route" {...props} />;
}

export function HighlightTransition(props: Omit<Parameters<typeof MotionSurface>[0], "motion">) {
  return <MotionSurface motion="highlight" {...props} />;
}

export function StaggerGroup({ children, className }: { children: ReactNode[]; className?: string }) {
  return (
    <div className={classes("ctv-stagger", className)}>
      {children.map((child, index) => (
        <div key={index} style={{ "--stagger-index": index } as CSSProperties}>
          {child}
        </div>
      ))}
    </div>
  );
}

export function ExpandCollapse({ open, children }: { open: boolean; children: ReactNode }) {
  return (
    <div className="ctv-expand" data-open={open ? "true" : "false"}>
      <div>{children}</div>
    </div>
  );
}

export function ReducedMotionBoundary({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
