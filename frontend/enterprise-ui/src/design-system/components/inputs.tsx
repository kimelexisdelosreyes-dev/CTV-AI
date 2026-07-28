import { ButtonHTMLAttributes, forwardRef, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { Search, X } from "lucide-react";
import { IconButton } from "./buttons";

type FieldShellProps = {
  label?: string;
  helperText?: string;
  errorText?: string;
  required?: boolean;
  children: ReactNode;
};

function FieldShell({ label, helperText, errorText, required, children }: FieldShellProps) {
  return (
    <label className="ctv-field">
      {label && <span className="ctv-field-label">{label}{required ? " *" : ""}</span>}
      {children}
      {errorText ? <span className="ctv-field-error">{errorText}</span> : helperText ? <span className="ctv-field-helper">{helperText}</span> : null}
    </label>
  );
}

export function TextInput({
  label,
  helperText,
  errorText,
  required,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & Omit<FieldShellProps, "children">) {
  return (
    <FieldShell label={label} helperText={helperText} errorText={errorText} required={required}>
      <input className="ctv-field-control" required={required} aria-invalid={Boolean(errorText)} {...props} />
    </FieldShell>
  );
}

export const SearchInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & {
  onClear?: () => void;
}>(function SearchInput({
  onClear,
  value,
  ...props
}, ref) {
  return (
    <div className="ctv-search-input">
      <Search size={16} />
      <input className="ctv-field-control" ref={ref} type="search" value={value} {...props} />
      {onClear && value ? <IconButton label="Clear search" onClick={onClear}><X size={14} /></IconButton> : null}
    </div>
  );
});

export function TextArea({
  label,
  helperText,
  errorText,
  required,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & Omit<FieldShellProps, "children">) {
  return (
    <FieldShell label={label} helperText={helperText} errorText={errorText} required={required}>
      <textarea className="ctv-field-control" required={required} aria-invalid={Boolean(errorText)} {...props} />
    </FieldShell>
  );
}

export function Select({
  label,
  helperText,
  errorText,
  required,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & Omit<FieldShellProps, "children">) {
  return (
    <FieldShell label={label} helperText={helperText} errorText={errorText} required={required}>
      <select className="ctv-field-control" required={required} aria-invalid={Boolean(errorText)} {...props}>
        {children}
      </select>
    </FieldShell>
  );
}

export function Checkbox({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return <label className="ctv-check-field"><input type="checkbox" {...props} /> {label}</label>;
}

export function Radio({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return <label className="ctv-check-field"><input type="radio" {...props} /> {label}</label>;
}

export function Switch({ label, checked, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="ctv-check-field">
      <input type="checkbox" checked={checked} style={{ position: "absolute", opacity: 0, pointerEvents: "none" }} {...props} />
      <span className="ctv-switch" data-checked={checked ? "true" : "false"} aria-hidden="true"><span className="ctv-switch__thumb" /></span>
      {label}
    </label>
  );
}

export function FilterChip({
  selected = false,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  selected?: boolean;
}) {
  return <button className="ctv-chip" data-selected={selected ? "true" : "false"} {...props}>{children}</button>;
}

export function TagInput({ tags }: { tags: string[] }) {
  return <div className="ctv-inline">{tags.map((tag) => <span className="ctv-chip" key={tag}>{tag}</span>)}</div>;
}
