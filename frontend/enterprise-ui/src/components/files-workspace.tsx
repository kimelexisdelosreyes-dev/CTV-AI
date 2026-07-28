"use client";

import { useMemo, useState } from "react";
import { Archive, Bot, Copy, FileSearch, FolderOpen, Link2, MapPin, Play, Sparkles, WifiOff } from "lucide-react";
import {
  AssetBadge, AssetIdentityCard, BaseCard, EmptyState, EnterpriseBreadcrumb, Inline, InlineAlert, Metadata, PageHeader, PageShell, PageTitle, PrimaryButton, RelationshipCard, RelationshipMap, RelationshipStrip, ResponsiveGrid, SearchInput, Section, StatusBadge, StorageHealthBadge, StorageLocationCard, VersionTimeline,
} from "@/design-system";
import { fileDiscoveryDemo } from "@/demo/adapters/experience";
import type { DemoFileResult } from "@/demo/types";

const demoQuery = "Interview_Lee_1987.mov";

const storage = [
  { copy: "Master Copy", source: "NAS 03 / CTV-NAS-01", status: "Offline", sync: "Yesterday", tone: "offline" as const, detail: "Indexed metadata remains available", action: "Reveal location" },
  { copy: "Working Copy", source: "Carl Workstation / EDIT-WS-02", status: "Online", sync: "12 minutes ago", tone: "healthy" as const, detail: "Editing proxy available", action: "Open copy" },
  { copy: "Proxy", source: "Google Drive", status: "Synced", sync: "Today, 09:42", tone: "processing" as const, detail: "Playback-ready proxy", action: "Preview" },
  { copy: "Archive", source: "Alibaba OSS", status: "Cold storage", sync: "Jun 18, 2026", tone: "neutral" as const, detail: "Retrieval may take time", action: "View archive" },
];

const events: Array<[string, string, string]> = [
  ["Today", "Summary generated", "My AI prepared a source-grounded summary."],
  ["Today", "Knowledge linked", "Archive interview handling guide connected."],
  ["Yesterday", "Master indexed", "CTV-NAS-01 metadata refreshed."],
  ["Earlier", "Transcript generated", "Transcript is available for review."],
  ["Earlier", "Created", "Imported into the Caloocan Fire Documentary archive."],
];

function AssetDetail({ asset }: { asset: DemoFileResult }) {
  return <>
    <Section><div className="files-section-heading"><div><span className="ctv-eyebrow">SELECTED ASSET</span><h2 className="ctv-section-title">Asset intelligence</h2></div><Inline><PrimaryButton leadingIcon={<FolderOpen size={15} />}>Open</PrimaryButton><button className="ctv-button ctv-button--secondary" type="button"><MapPin size={15} /> Reveal Location</button></Inline></div>
      <AssetIdentityCard asset={asset} />
    </Section>
    <Section><h2 className="ctv-section-title">Storage locations</h2><ResponsiveGrid min="230px">{storage.map((item) => <StorageLocationCard key={item.copy} {...item} />)}</ResponsiveGrid></Section>
    <Section><EnterpriseBreadcrumb items={["Workspace", "Caloocan Fire Documentary", "Interview", "Interview_Lee_1987.mov"]} /><h2 className="ctv-section-title">Relationship graph</h2><RelationshipStrip items={[{ type: "Project", title: "Fire Documentary", tone: "processing" }, { type: "File", title: "Interview", tone: "healthy" }, { type: "Transcript", title: "Transcript", tone: "healthy" }, { type: "Knowledge", title: "Knowledge", tone: "healthy" }, { type: "AI Summary", title: "Summary", tone: "healthy" }]} /><RelationshipMap items={[{ type: "Project", title: "Caloocan Fire Documentary" }, { type: "File", title: asset.title, tone: "healthy" }, { type: "Transcript", title: "Lee Chin transcript", tone: "healthy" }, { type: "Knowledge", title: "Handling guide", tone: "healthy" }, { type: "AI Summary", title: "Interview summary", tone: "healthy" }]} /><div className="files-relationship-graph">{[["Project", "Caloocan Fire Documentary", "In review"], ["Knowledge", "Archive interview handling guide", "Approved"], ["Transcript", "Lee Chin interview transcript", "Available"], ["AI Summary", "Interview summary prepared", "Ready"], ["Person", "Mina Lee / Executive Producer", "Linked"], ["Collection", "Fire Documentary / Interviews", "Linked"]].map(([type, title, status]) => <RelationshipCard key={type} relationship={{ type: type as "Project", title, status }} onOpen={() => undefined} />)}</div></Section>
    <Section><div className="files-detail-columns"><div><h2 className="ctv-section-title">Version history</h2><VersionTimeline events={events} /></div><div><h2 className="ctv-section-title">AI intelligence</h2><div className="files-ai-panel"><div className="files-ai-status"><Sparkles size={17} /><strong>AI ready</strong><StatusBadge status="healthy">6 signals</StatusBadge></div><p>Transcript and summary are available. OCR is complete for the linked archive still. Duplicate candidate detected in Google Drive.</p><Inline><StatusBadge status="healthy">Transcript available</StatusBadge><StatusBadge status="healthy">OCR complete</StatusBadge><StatusBadge status="warning">Duplicate detected</StatusBadge></Inline></div></div></div></Section>
    <Section><h2 className="ctv-section-title">Recommended actions</h2><ResponsiveGrid min="220px">{[{ icon: <Play size={16} />, title: "Review Summary", detail: "Open the prepared interview summary." }, { icon: <Copy size={16} />, title: "Compare Versions", detail: "Review the Drive duplicate candidate." }, { icon: <Archive size={16} />, title: "Archive Asset", detail: "Move the approved master to cold storage." }, { icon: <Bot size={16} />, title: "View Knowledge", detail: "Open linked handling guidance." }].map((item) => <BaseCard key={item.title} title={<Inline>{item.icon}{item.title}</Inline>} meta="Recommended" interactive><Metadata>{item.detail}</Metadata></BaseCard>)}</ResponsiveGrid></Section>
  </>;
}

export function FilesWorkspace() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState(demoQuery);
  const [selectedId, setSelectedId] = useState("master");
  const results = useMemo(() => fileDiscoveryDemo(submitted, "success"), [submitted]);
  const selected = results.find((item) => item.id === selectedId) ?? results[0];
  function runDiscovery() { setSubmitted(query.trim() || demoQuery); }
  return <PageShell>
    <PageHeader eyebrow="ENTERPRISE FILE DISCOVERY" title={<PageTitle>Files</PageTitle>} description={<p className="ctv-body">A source of truth for enterprise assets, their locations, relationships, and next actions. Demonstration data.</p>} action={<StatusBadge status="processing">Asset intelligence ready</StatusBadge>} />
    <BaseCard className="files-quick-summary" title={selected?.title ?? demoQuery} meta="Master copy / CTV-NAS-01 / indexed metadata"><div className="files-summary-grid"><div><Metadata>Status</Metadata><strong>Master identified</strong></div><div><Metadata>Owner</Metadata><strong>Production Archive</strong></div><div><Metadata>Project</Metadata><strong>Caloocan Fire Documentary</strong></div><div><Metadata>Modified</Metadata><strong>Yesterday, 16:20</strong></div><div><Metadata>Storage health</Metadata><StorageHealthBadge status="offline" /></div></div><Inline><PrimaryButton leadingIcon={<FolderOpen size={15} />}>Open</PrimaryButton><button className="ctv-button ctv-button--secondary" type="button"><Link2 size={15} /> View Relationships</button></Inline></BaseCard>
    <BaseCard title="Find an enterprise asset" meta="Search indexed files, copies, projects, and related knowledge"><Inline><SearchInput aria-label="Search Enterprise Assets" placeholder={demoQuery} value={query} onChange={(e) => setQuery(e.target.value)} onClear={() => setQuery("")} /><PrimaryButton leadingIcon={<FileSearch size={16} />} onClick={runDiscovery}>Search Assets</PrimaryButton></Inline></BaseCard>
    {selected ? <AssetDetail asset={selected} /> : <EmptyState title="No asset selected">Search indexed enterprise assets to inspect identity, storage, and relationships.</EmptyState>}
    <InlineAlert title="Indexed metadata and availability" status="warning"><WifiOff size={15} /> CTV-NAS-01 is offline; indexed metadata is visible, while source content remains unavailable until the location returns online.</InlineAlert>
  </PageShell>;
}
