import type { SearchProviderResponse, SearchQuery } from "@/contracts/search";
import { BaseProvider, type ProviderContext } from "../../sdk";
import { localKnowledgeRecords } from "./local-knowledge-source";
import { normalizeLocalKnowledge } from "./local-knowledge-normalizer";
export class LocalKnowledgeSearchProvider extends BaseProvider { readonly id = "local-knowledge"; readonly name = "Local Knowledge"; readonly capabilities = ["search"] as const; protected async execute(query: SearchQuery, context: ProviderContext): Promise<SearchProviderResponse> { if (context.signal.aborted) return { status: "cancelled", results: [], durationMs: 0 }; const terms = query.text.toLowerCase().split(/\s+/).filter(Boolean); return { status: "ready", results: localKnowledgeRecords().filter((record) => terms.some((term) => `${record.title} ${record.meta} ${record.category} ${record.tags.join(" ")}`.toLowerCase().includes(term))).map(normalizeLocalKnowledge), durationMs: 0 }; } }
