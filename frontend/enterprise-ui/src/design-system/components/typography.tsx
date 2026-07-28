import { HTMLAttributes, ReactNode } from "react";

type TextProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

function textClass(base: string, className?: string): string {
  return className ? `${base} ${className}` : base;
}

export function Display({ children, className, ...props }: TextProps) {
  return <h1 className={textClass("ctv-display", className)} {...props}>{children}</h1>;
}

export function PageTitle({ children, className, ...props }: TextProps) {
  return <h1 className={textClass("ctv-page-title", className)} {...props}>{children}</h1>;
}

export function SectionTitle({ children, className, ...props }: TextProps) {
  return <h2 className={textClass("ctv-section-title", className)} {...props}>{children}</h2>;
}

export function CardTitle({ children, className, ...props }: TextProps) {
  return <h3 className={textClass("ctv-card-title", className)} {...props}>{children}</h3>;
}

export function Body({ children, className, ...props }: TextProps) {
  return <p className={textClass("ctv-body", className)} {...props}>{children}</p>;
}

export function Metadata({ children, className, ...props }: TextProps) {
  return <p className={textClass("ctv-metadata", className)} {...props}>{children}</p>;
}

export function Caption({ children, className, ...props }: TextProps) {
  return <span className={textClass("ctv-caption", className)} {...props}>{children}</span>;
}

