import { ReactNode } from "react";
import { Database, FileText, Folder, HardDrive, Network, Server, ShieldCheck, Wifi } from "lucide-react";
import { BaseCard } from "./cards";
import { StatusBadge } from "./status";
import { Metadata } from "./typography";
import { StatusTone } from "../tokens";

export function FileVersionBadge({ version }: { version: string }) {
  return <StatusBadge status="neutral">v{version}</StatusBadge>;
}

export function MasterCopyBadge() {
  return <StatusBadge status="healthy">Master copy</StatusBadge>;
}

export function WorkingCopyBadge() {
  return <StatusBadge status="processing">Working copy</StatusBadge>;
}

export function ProxyBadge() {
  return <StatusBadge status="neutral">Proxy</StatusBadge>;
}

export function ArchiveBadge() {
  return <StatusBadge status="offline">Archive</StatusBadge>;
}

export function DuplicateBadge() {
  return <StatusBadge status="warning">Duplicate</StatusBadge>;
}

export function WorkstationBadge({ name }: { name: string }) {
  return <StatusBadge status="processing">{name}</StatusBadge>;
}

export function StorageSourceBadge({ source }: { source: string }) {
  return <StatusBadge status="neutral">{source}</StatusBadge>;
}

export function FileLocationCard({
  source,
  owner,
  drive,
  path,
  online,
  lastIndexed,
  access,
}: {
  source: string;
  owner: string;
  drive: string;
  path: string;
  online: boolean;
  lastIndexed: string;
  access: string;
}) {
  return (
    <BaseCard title={source} meta={path} action={<StatusBadge status={online ? "healthy" : "offline"}>{online ? "Online" : "Offline"}</StatusBadge>}>
      <Metadata>Owner: {owner}</Metadata>
      <Metadata>Drive or mount: {drive}</Metadata>
      <Metadata>Last indexed: {lastIndexed}</Metadata>
      <Metadata>Access: {access}</Metadata>
    </BaseCard>
  );
}

function NodeCard({ title, icon, status = "neutral", children }: { title: string; icon: ReactNode; status?: StatusTone; children?: ReactNode }) {
  return <BaseCard title={<span className="ctv-inline">{icon}{title}</span>} action={<StatusBadge status={status} />}>{children}</BaseCard>;
}

export function EnterpriseMapNode(props: { title: string; status?: StatusTone; children?: ReactNode }) {
  return <NodeCard icon={<Network size={18} />} {...props} />;
}

export function WorkstationNode(props: { title: string; status?: StatusTone; children?: ReactNode }) {
  return <NodeCard icon={<HardDrive size={18} />} {...props} />;
}

export function StorageNode(props: { title: string; status?: StatusTone; children?: ReactNode }) {
  return <NodeCard icon={<Database size={18} />} {...props} />;
}

export function CloudNode(props: { title: string; status?: StatusTone; children?: ReactNode }) {
  return <NodeCard icon={<Server size={18} />} {...props} />;
}

export function AIServiceNode(props: { title: string; status?: StatusTone; children?: ReactNode }) {
  return <NodeCard icon={<ShieldCheck size={18} />} {...props} />;
}

export function IntegrationNode(props: { title: string; status?: StatusTone; children?: ReactNode }) {
  return <NodeCard icon={<Folder size={18} />} {...props} />;
}

export function ConnectionStatus({ online }: { online: boolean }) {
  return <StatusBadge status={online ? "healthy" : "offline"}><Wifi size={13} />{online ? "Connected" : "Unavailable"}</StatusBadge>;
}

export function SystemHealthSummary({ healthy, detail }: { healthy: boolean; detail: string }) {
  return <BaseCard title="Enterprise Infrastructure" action={<StatusBadge status={healthy ? "healthy" : "warning"}>{healthy ? "Healthy" : "Needs attention"}</StatusBadge>}><Metadata>{detail}</Metadata></BaseCard>;
}

export function AssetBadge({ state }: { state: "master" | "working" | "proxy" | "archive" | "duplicate" | "missing" }) {
  const labels = { master: "Master", working: "Working", proxy: "Proxy", archive: "Archive", duplicate: "Duplicate", missing: "Missing" };
  const tones = { master: "healthy", working: "processing", proxy: "neutral", archive: "offline", duplicate: "warning", missing: "critical" } as const;
  return <StatusBadge status={tones[state]}>{labels[state]}</StatusBadge>;
}

export function StorageHealthBadge({ status }: { status: "healthy" | "offline" | "processing" | "neutral" }) {
  return <StatusBadge status={status}>{status === "healthy" ? "Healthy" : status === "processing" ? "Synced" : status === "offline" ? "Offline" : "Cold storage"}</StatusBadge>;
}

export function AssetIdentityCard({ asset }: { asset: { title: string; source: string; owner: string; path: string; availability: string; version: string; relatedProject: string } }) {
  return <BaseCard className="asset-identity-card" title={<span className="ctv-inline"><FileText size={18} />{asset.title}</span>} meta={asset.path} action={<AssetBadge state={asset.version === "3" ? "master" : "duplicate"} />}><div className="files-identity-grid"><span>Asset ID<strong>asset-lee-1987-001</strong></span><span>Owner<strong>{asset.owner}</strong></span><span>Primary project<strong>{asset.relatedProject}</strong></span><span>File size<strong>4.8 GB</strong></span><span>Resolution<strong>4K UHD</strong></span><span>Duration<strong>42:18</strong></span><span>Created<strong>Jun 12, 2026</strong></span><span>Modified<strong>Yesterday, 16:20</strong></span><span>Checksum<strong>Not available</strong></span><span>Storage source<strong>{asset.source}</strong></span></div><Metadata>Checksum verification is unavailable in this demonstration adapter.</Metadata></BaseCard>;
}

export function StorageLocationCard({ copy, source, status, sync, tone, detail, action }: { copy: string; source: string; status: string; sync: string; tone: "healthy" | "offline" | "processing" | "neutral"; detail: string; action: string }) {
  return <BaseCard className="storage-location-card" title={copy} meta={source} action={<StorageHealthBadge status={tone} />}><Metadata>{detail}</Metadata><div className="storage-location-meta"><span>Last sync<strong>{sync}</strong></span><button className="ctv-link-button" type="button">{action}</button></div></BaseCard>;
}

export function VersionTimeline({ events }: { events: Array<[string, string, string]> }) {
  return <ol className="files-version-timeline" aria-label="Asset version history">{events.map(([group, title, detail]) => <li key={`${group}-${title}`}><span className="files-timeline-dot" aria-hidden="true" /><div><Metadata>{group}</Metadata><strong>{title}</strong><p>{detail}</p></div></li>)}</ol>;
}
