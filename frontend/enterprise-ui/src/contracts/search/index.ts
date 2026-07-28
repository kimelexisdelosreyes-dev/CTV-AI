export type SearchEntityType = "project" | "file" | "knowledge" | "person" | "workstation" | "storage" | "service" | "ai-job" | "setting";
export type SearchProviderStatus = "ready" | "partial" | "offline" | "unauthorized" | "timeout" | "unavailable" | "error" | "cancelled";
export type SearchContext = { module?: string; projectId?: string; owner?: string; signal?: AbortSignal };
export type SearchQuery = { text: string; limit?: number; context?: SearchContext };
export type SearchRelationship = { type: string; label: string; confidence?: number };
export type SearchResult = { key: string; title: string; type: SearchEntityType; providerId: string; score?: number; relevance?: number; updatedAt?: string; canonicalUri?: string; metadata?: Record<string, string>; relationships?: SearchRelationship[]; temporalEvidence?: readonly TemporalEvidence[] };
export type SearchProviderResponse = { status: SearchProviderStatus; results: SearchResult[]; durationMs: number; diagnostic?: string };
export type SearchProviderCapability = "search" | "relationships";
export interface ISearchProvider { readonly id: string; readonly name: string; readonly capabilities: readonly SearchProviderCapability[]; supports(query: SearchQuery): boolean; search(query: SearchQuery, context: SearchContext, signal: AbortSignal): Promise<SearchProviderResponse>; health(): SearchProviderStatus; }
export interface ISearchRegistry { register(provider: ISearchProvider, priority?: number): void; unregister(id: string): boolean; list(): readonly ISearchProvider[]; discover(capability?: SearchProviderCapability): readonly ISearchProvider[]; health(id: string): SearchProviderStatus | undefined; }
export interface ISearchRanking { rank(results: SearchResult[], query: SearchQuery): SearchResult[]; }
export interface ISearchCache { get(key: string): SearchResult[] | undefined; set(key: string, value: SearchResult[], ttlMs: number, providerIds: string[]): void; invalidate(key?: string): void; clear(): void; size(): number; }
export type SearchProviderDiagnostic = { providerId: string; status: SearchProviderStatus; durationMs: number; resultCount: number; diagnostic?: string };
export type SearchDiagnostics = { queryId: string; providersSelected: string[]; providersCompleted: string[]; durationMs: number; resultCount: number; partialResultCount: number; timeoutCount: number; errorCount: number; cache: "hit" | "miss" };
export type SearchResponse = { results: SearchResult[]; providers: SearchProviderDiagnostic[]; diagnostics: SearchDiagnostics };
export interface ISearchService { search(query: SearchQuery): Promise<SearchResponse>; }
import type { TemporalEvidence } from "@/contracts/temporal";
