import { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonSize = "small" | "medium" | "large";
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  loading?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

const labels: Record<ButtonVariant, string> = {
  primary: "ctv-button--primary",
  secondary: "ctv-button--secondary",
  ghost: "ctv-button--ghost",
  danger: "ctv-button--danger",
  success: "ctv-button--success",
};

function sizeClass(size: ButtonSize): string {
  if (size === "small") return "ctv-button--small";
  if (size === "large") return "ctv-button--large";
  return "";
}

export function Button({
  children,
  leadingIcon,
  trailingIcon,
  loading = false,
  disabled,
  size = "medium",
  variant = "primary",
  className,
  ...props
}: ButtonProps) {
  const classNames = ["ctv-button", labels[variant], sizeClass(size), className]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classNames} disabled={disabled || loading} {...props}>
      {loading ? <span className="ctv-spinner" aria-hidden="true" /> : leadingIcon}
      {children}
      {trailingIcon}
    </button>
  );
}

export function PrimaryButton(props: Omit<ButtonProps, "variant">) {
  return <Button variant="primary" {...props} />;
}

export function SecondaryButton(props: Omit<ButtonProps, "variant">) {
  return <Button variant="secondary" {...props} />;
}

export function GhostButton(props: Omit<ButtonProps, "variant">) {
  return <Button variant="ghost" {...props} />;
}

export function DangerButton(props: Omit<ButtonProps, "variant">) {
  return <Button variant="danger" {...props} />;
}

export function SuccessButton(props: Omit<ButtonProps, "variant">) {
  return <Button variant="success" {...props} />;
}

export function IconButton({
  label,
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  children: ReactNode;
}) {
  return (
    <button aria-label={label} title={label} className={["ctv-icon-button", className].filter(Boolean).join(" ")} {...props}>
      {children}
    </button>
  );
}

export function SplitButton({
  primary,
  menu,
}: {
  primary: ReactNode;
  menu: ReactNode;
}) {
  return (
    <span className="ctv-inline" role="group">
      {primary}
      {menu}
    </span>
  );
}

