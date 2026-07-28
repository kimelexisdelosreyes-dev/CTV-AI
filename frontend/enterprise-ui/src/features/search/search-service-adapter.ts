import type { ISearchService, SearchQuery } from "@/contracts/search";
import { buildSearchViewModel } from "./search-intelligence";
import type { RichSearchResult, SearchActionTarget, SearchViewModel } from "./search-types";
import { ContextEngine, contributionsFromSearchResults } from "@/services/context";
import { createGraphRuntimeService, GraphRuntimeQueryService, relationshipPresentationFromNeighborhood } from "@/services/graph";
import { createMemoryRuntimeService } from "@/services/memory/createMemoryRuntimeService";

// Application-scoped coordinator: UI passes explicit context, services own immutable snapshots.
const contextEngine = new ContextEngine();
const graphRuntime = createGraphRuntimeService();
const graphQuery = new GraphRuntimeQueryService(graphRuntime);
const memoryRuntime = createMemoryRuntimeService();

export function relationshipPresentationForSearchResult(result: RichSearchResult) { const query = graphQuery.selected({ id: result.id }); return { ...relationshipPresentationFromNeighborhood(query.neighborhood, result.relationships), resolution: query.resolution }; }

export async function searchWithService(service: ISearchService, text: string, context?: SearchQuery["context"]): Promise<SearchViewModel> {
  const response = await service.search({ text, context });
  const presentationSeed = buildSearchViewModel(text, (context?.module as SearchActionTarget | undefined) ?? "overview");
  const byId = new Map(presentationSeed.flatResults.map((result) => [result.id, result]));
  const byTitle = new Map(presentationSeed.flatResults.map((result) => [result.title, result.id]));
  const graphResults = response.results.map((result) => { const presentation = byId.get(result.key); return presentation ? { ...result, relationships: presentation.relationships.map((relationship) => ({ type: relationship.label === "Project" ? "belongs_to" : relationship.label === "Storage" ? "stored_on" : "related_to", label: byTitle.get(relationship.value) ?? relationship.value, confidence: 1 })) } : result; });
  const contextSnapshot = await contextEngine.snapshot({ module: context?.module, projectId: context?.projectId }, contributionsFromSearchResults(graphResults));
  const graphResult = await graphRuntime.build(contextSnapshot, context?.signal);
  if (graphResult.session && graphResult.status === "ready") await memoryRuntime.build(contextSnapshot, graphResult.session, context?.signal);
  const flatResults = response.results.map((result) => {
    const existing = byId.get(result.key);
    if (existing) return { ...existing, metadata: result.metadata?.meta ? [...existing.metadata, result.metadata.meta] : existing.metadata };
    return {
      id: result.key, title: result.title, category: "Files", kind: result.type, iconLabel: result.type, status: "Available", tone: "neutral", metadata: Object.values(result.metadata ?? {}), summary: "Normalized result from Enterprise Search.", action: "Open result", target: "overview", relationships: [], preview: [],
    } as RichSearchResult;
  });
  const groups = ["Projects", "Files", "Knowledge", "People", "Workstations", "AI Jobs", "Settings"].map((category) => ({ category: category as SearchViewModel["groups"][number]["category"], results: flatResults.filter((result) => result.category === category) })).filter((group) => group.results.length > 0);
  return { ...presentationSeed, query: text, state: response.diagnostics.errorCount > 0 ? "partial" : flatResults.length ? "completed" : "no-results", flatResults, groups, announcement: `${flatResults.length} result${flatResults.length === 1 ? "" : "s"} from Enterprise Search.` };
}
