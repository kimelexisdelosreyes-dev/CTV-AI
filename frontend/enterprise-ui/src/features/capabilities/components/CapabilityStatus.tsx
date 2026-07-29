type CapabilityStatusLabel = "Available" | "Healthy" | "Beta" | "Maintenance" | "Disabled" | "Coming Soon";

export function CapabilityStatus({ label = "Available" }: { label?: CapabilityStatusLabel }) {
  return <span className={`capability-status capability-status--${label.toLowerCase().replace(/\s/g, "-")}`} aria-label={`Capability status: ${label}`}>{label}</span>;
}
