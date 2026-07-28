import { demoFileResults } from "@/demo/data/experience";
import type { DemoFileResult } from "@/demo/types";
export type LocalFileRecord = DemoFileResult & { tags: string[]; modified: string; sourceModifiedAt: string; sourceReferenceId: string };
// These are source-metadata timestamps in the deterministic local-demo adapter, not provider fetch times.
const sourceModifiedAt: Record<string, string> = { master: "2026-06-18T16:20:00Z", proxy: "2026-06-17T09:45:00Z", duplicate: "2026-06-16T14:10:00Z", "oss-archive": "2026-06-12T08:30:00Z" };
export function localFileRecords(): LocalFileRecord[] { return demoFileResults.map((record) => ({ ...record, tags: [record.copyState, "archive", record.relatedProject], modified: "Yesterday", sourceModifiedAt: sourceModifiedAt[record.id] ?? "", sourceReferenceId: `local-file-record:${record.id}` })); }
