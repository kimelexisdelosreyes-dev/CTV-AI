import { demoSearchResults } from "@/demo/data/experience";
import type { DemoSearchResult } from "@/demo/types";
export type LocalKnowledgeRecord = DemoSearchResult & { tags: string[]; sourceMode: "local-demo"; sourceModifiedAt: string; sourceReferenceId: string };
const sourceModifiedAt: Record<string, string> = { "knowledge-fire-policy": "2026-06-10T11:05:00Z" };
export function localKnowledgeRecords(): LocalKnowledgeRecord[] { return demoSearchResults.filter((record) => record.category === "Knowledge").map((record) => ({ ...record, tags: ["Production", "Approved"], sourceMode: "local-demo", sourceModifiedAt: sourceModifiedAt[record.id] ?? "", sourceReferenceId: `local-knowledge-record:${record.id}` })); }
