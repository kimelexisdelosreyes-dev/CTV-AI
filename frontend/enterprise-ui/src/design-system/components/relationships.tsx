import { ArrowRight, Link2 } from "lucide-react";
import { ReactNode } from "react";
import { BaseCard } from "./cards";
import { StatusBadge } from "./status";
import { Metadata } from "./typography";
import { StatusTone } from "../tokens";

export type RelationshipType = "Project" | "File" | "Knowledge" | "Person" | "Storage" | "Workstation" | "Transcript" | "OCR" | "AI Summary" | "Collection" | "Service" | "AI Job";
export type PresentationRelationship = { type: RelationshipType; title: string; subtitle?: string; status?: string; tone?: StatusTone; metadata?: string; icon?: ReactNode };

export function RelationshipBadge({ type, tone = "neutral" }: { type: RelationshipType; tone?: StatusTone }) { return <StatusBadge status={tone}>{type}</StatusBadge>; }

export function RelationshipCard({ relationship, onOpen }: { relationship: PresentationRelationship; onOpen?: () => void }) {
  return <BaseCard className="relationship-card" title={<span className="ctv-inline">{relationship.icon ?? <Link2 size={15} />}{relationship.title}</span>} meta={relationship.subtitle} action={<RelationshipBadge type={relationship.type} tone={relationship.tone} />} interactive={Boolean(onOpen)} onClick={onOpen}><Metadata>{relationship.metadata ?? relationship.status ?? "Connected"}</Metadata>{onOpen ? <span className="relationship-card__action">Open relationship <ArrowRight size={13} /></span> : null}</BaseCard>;
}

export function RelationshipStrip({ items }: { items: PresentationRelationship[] }) { return <nav className="relationship-strip" aria-label="Enterprise relationship path">{items.map((item, index) => <span className="relationship-strip__item" key={`${item.type}-${item.title}`}><RelationshipBadge type={item.type} tone={item.tone} /><strong>{item.title}</strong>{index < items.length - 1 ? <ArrowRight size={14} aria-hidden="true" /> : null}</span>)}</nav>; }

export function RelationshipMap({ items }: { items: PresentationRelationship[] }) { return <div className="relationship-map" aria-label="Mini relationship map" role="list">{items.map((item) => <div className="relationship-map__node" key={`${item.type}-${item.title}`} role="listitem"><RelationshipBadge type={item.type} tone={item.tone} /><strong>{item.title}</strong></div>)}</div>; }

export function RelatedObjectsPanel({ groups }: { groups: Array<{ label: string; items: PresentationRelationship[] }> }) { return <section className="related-objects-panel" aria-label="Related enterprise objects">{groups.map((group) => <details key={group.label} open><summary>{group.label} <span>{group.items.length}</span></summary><div className="related-objects-panel__items">{group.items.map((item) => <RelationshipCard key={`${group.label}-${item.title}`} relationship={item} />)}</div></details>)}</section>; }

export function EnterpriseBreadcrumb({ items }: { items: string[] }) { return <nav className="enterprise-breadcrumb" aria-label="Enterprise context">{items.map((item, index) => <span key={`${item}-${index}`}>{item}{index < items.length - 1 ? <ArrowRight size={13} aria-hidden="true" /> : null}</span>)}</nav>; }

export function RelationshipTimeline({ items }: { items: Array<{ title: string; detail: string; time: string }> }) { return <ol className="relationship-timeline" aria-label="Related activity">{items.map((item) => <li key={`${item.time}-${item.title}`}><strong>{item.title}</strong><Metadata>{item.detail}</Metadata><span>{item.time}</span></li>)}</ol>; }
