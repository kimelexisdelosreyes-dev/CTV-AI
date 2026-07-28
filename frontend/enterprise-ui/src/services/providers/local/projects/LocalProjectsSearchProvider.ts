import type { SearchProviderResponse, SearchQuery } from "@/contracts/search";
import { BaseProvider, type ProviderContext } from "../../sdk";
import { localProjectRecords } from "./local-projects-source";
import { normalizeLocalProject } from "./local-projects-normalizer";
export class LocalProjectsSearchProvider extends BaseProvider { readonly id = "local-projects"; readonly name = "Local Projects"; readonly capabilities = ["search"] as const; protected async execute(query: SearchQuery, context: ProviderContext): Promise<SearchProviderResponse> { if (context.signal.aborted) return { status: "cancelled", results: [], durationMs: 0 }; const terms = query.text.toLowerCase().split(/\s+/).filter(Boolean); return { status: "ready", results: localProjectRecords().filter((record) => terms.some((term) => `${record.title} ${record.meta} ${record.code} ${record.department}`.toLowerCase().includes(term))).map(normalizeLocalProject), durationMs: 0 }; } }
