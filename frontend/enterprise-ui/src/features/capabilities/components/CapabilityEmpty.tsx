export function CapabilityEmpty({ title = "Capability workspace", message }: { title?: string; message: string }) {
  return <section className="capability-empty" aria-live="polite"><h2>{title}</h2><p>{message}</p></section>;
}
