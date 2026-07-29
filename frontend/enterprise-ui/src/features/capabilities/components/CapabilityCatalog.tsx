import { CapabilityStatus } from "./CapabilityStatus";
import type { CapabilitySummary } from "../api";

export function CapabilityCatalog({ items, selectedId, onSelect }: { items: CapabilitySummary[]; selectedId?: string; onSelect: (item: CapabilitySummary) => void }) {
  return <section className="capability-catalog" aria-label="Capability catalog">
    <div className="capability-panel-heading"><div><p className="capability-kicker">Capability catalog</p><h2>Available tools</h2></div><span>{items.length} available</span></div>
    <div className="capability-catalog__items">
      {items.map((item) => <button className="capability-catalog__item" key={item.capability_id} type="button" aria-pressed={selectedId === item.capability_id} onClick={() => onSelect(item)}><span><strong>{item.name}</strong><small>{item.description}</small></span><CapabilityStatus /></button>)}
    </div>
  </section>;
}
