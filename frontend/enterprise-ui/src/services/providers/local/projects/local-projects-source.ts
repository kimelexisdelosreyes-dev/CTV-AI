import { demoSearchResults } from "@/demo/data/experience";
import type { DemoSearchResult } from "@/demo/types";
export type LocalProjectRecord = DemoSearchResult & { code: string; department: string; sourceMode: "local-demo"; sourceCreatedAt: string; sourceReferenceId: string };
const sourceCreatedAt: Record<string, string> = { "project-fire-doc": "2026-01-12" };
export function localProjectRecords(): LocalProjectRecord[] { return demoSearchResults.filter((record) => record.category === "Projects").map((record) => ({ ...record, code: "CFD-1987", department: "Production", sourceMode: "local-demo", sourceCreatedAt: sourceCreatedAt[record.id] ?? "", sourceReferenceId: `local-project-record:${record.id}` })); }
