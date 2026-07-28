import { searchDemo } from "@/demo/adapters/experience";
import type { SearchProviderResponse, SearchQuery } from "@/contracts/search";
import { BaseProvider, type ProviderContext } from "../sdk";

export class DemoSearchProvider extends BaseProvider {
  readonly id = "demo-search";
  readonly name = "Demo Search Adapter";
  readonly capabilities = ["search"] as const;

  protected async execute(query: SearchQuery, _context: ProviderContext): Promise<SearchProviderResponse> {
    const started = Date.now();
    const results = searchDemo(query.text, "success").map((item) => ({
      key: item.id,
      title: item.title,
      type: item.category === "Projects" ? "project" : item.category === "Files" ? "file" : item.category === "Knowledge" ? "knowledge" : item.category === "People" ? "person" : item.category === "AI Jobs" ? "ai-job" : "setting",
      providerId: this.id,
      relevance: item.title.toLowerCase() === query.text.toLowerCase() ? 100 : 20,
      metadata: { meta: item.meta },
    } as const));
    return { status: "ready", results, durationMs: Date.now() - started };
  }
}
