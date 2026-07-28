import type { ISearchRanking, SearchQuery, SearchResult } from "@/contracts/search";
export class SearchRanking implements ISearchRanking {
  rank(results: SearchResult[], query: SearchQuery) {
    const needle = query.text.trim().toLowerCase();
    const typeWeight: Record<string, number> = { project: 6, file: 5, knowledge: 4, person: 3, "ai-job": 2 };
    return results.map((result, index) => { const title = result.title.toLowerCase(); const exact = title === needle ? 100 : title.includes(needle) ? 30 : 0; const context = query.context?.projectId && result.metadata?.projectId === query.context.projectId ? 12 : 0; return { result, score: exact + context + (result.relevance ?? 0) + (typeWeight[result.type] ?? 0), index }; }).sort((a, b) => b.score - a.score || a.index - b.index).map(({ result, score }) => ({ ...result, score }));
  }
}
