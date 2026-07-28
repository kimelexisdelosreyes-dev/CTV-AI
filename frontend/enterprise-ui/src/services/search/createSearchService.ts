import type { ISearchService } from "@/contracts/search";
import { TelemetryService } from "../telemetry";
import { DemoSearchProvider } from "../providers/demo";
import { ComputeProvider, InfrastructureProvider, LocalFilesSearchProvider, LocalKnowledgeSearchProvider, LocalProjectsSearchProvider, StorageProvider, WorkstationProvider } from "../providers/local";
import { SearchCache } from "./SearchCache";
import { SearchRanking } from "./SearchRanking";
import { SearchRegistry } from "./SearchRegistry";
import { SearchService } from "./SearchService";

export function createSearchService(): ISearchService {
  const registry = new SearchRegistry();
  registry.register(new DemoSearchProvider(), 10);
  registry.register(new LocalFilesSearchProvider(), 20);
  registry.register(new LocalKnowledgeSearchProvider(), 15);
  registry.register(new LocalProjectsSearchProvider(), 15);
  registry.register(new WorkstationProvider(), 14);
  registry.register(new ComputeProvider(), 13);
  registry.register(new InfrastructureProvider(), 12);
  registry.register(new StorageProvider(), 12);
  return new SearchService(registry, new SearchRanking(), new SearchCache(), new TelemetryService(false));
}
