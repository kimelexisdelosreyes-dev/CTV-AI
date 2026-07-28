import { ReactNode } from "react";
import { Search } from "lucide-react";
import { BaseCard } from "./cards";
import { EmptyState } from "./feedback";
import { SearchInput } from "./inputs";
import { StatusBadge } from "./status";
import { CardTitle, Metadata } from "./typography";
import { StatusTone } from "../tokens";

export function CommandPalette({ children }: { children: ReactNode }) {
  return <div className="ctv-card" role="dialog" aria-modal="true" aria-label="Command palette">{children}</div>;
}

export function SearchOverlay({ value, onChange, children }: { value: string; onChange: (value: string) => void; children: ReactNode }) {
  return <CommandPalette><SearchInput aria-label="Search CTV ONE" placeholder="Search projects, files, knowledge, people, and commands" value={value} onChange={(event) => onChange(event.target.value)} />{children}</CommandPalette>;
}

export function SearchGroup({ title, children }: { title: string; children: ReactNode }) {
  return <section className="ctv-section"><CardTitle>{title}</CardTitle>{children}</section>;
}

export function SearchResultItem({ title, meta, category }: { title: string; meta: string; category: string }) {
  return <BaseCard title={<span className="ctv-inline"><Search size={16} />{title}</span>} meta={meta} action={<StatusBadge status="neutral">{category}</StatusBadge>} interactive />;
}

export function SearchSourceStatus({ label, available }: { label: string; available: boolean }) {
  return <StatusBadge status={available ? "healthy" : "offline"}>{label}</StatusBadge>;
}

export function SearchPreview({ title, meta, children }: { title: string; meta: string; children: ReactNode }) {
  return <BaseCard title={title} meta={meta} className="search-preview-panel">{children}</BaseCard>;
}

export function SearchBadge({ children, status = "neutral" }: { children: ReactNode; status?: StatusTone }) {
  return <StatusBadge status={status}>{children}</StatusBadge>;
}

export function SearchMetadata({ children }: { children: ReactNode }) {
  return <Metadata>{children}</Metadata>;
}

export function RecentSearch({ label }: { label: string }) {
  return <button className="ctv-chip" type="button">{label}</button>;
}

export function SuggestionCard({ label, context }: { label: string; context: string }) {
  return <BaseCard title={label} meta={context} interactive />;
}

export function SearchHighlight({ children }: { children: ReactNode }) {
  return <mark className="search-highlight">{children}</mark>;
}

export function SearchEmptyState() {
  return <EmptyState title="No matching results">Try a project, file, Knowledge Center source, person, AI job, or setting you can access.</EmptyState>;
}

export const searchCategories = ["Projects", "Files", "Knowledge", "People", "Workstations", "AI Jobs", "Settings"] as const;

export function SearchCategoryList() {
  return <Metadata>{searchCategories.join(" / ")}</Metadata>;
}
