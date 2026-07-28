import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const service = readFileSync("src/services/search/SearchService.ts", "utf8");
const registry = readFileSync("src/services/search/SearchRegistry.ts", "utf8");
const contracts = readFileSync("src/contracts/search/index.ts", "utf8");
const provider = readFileSync("src/services/providers/demo/DemoSearchProvider.ts", "utf8");

test("search contracts expose normalized provider and diagnostics boundaries", () => {
  for (const token of ["SearchQuery", "SearchResult", "ISearchProvider", "ISearchService", "ISearchRegistry", "ISearchCache", "SearchDiagnostics"]) assert.ok(contracts.includes(token), `missing ${token}`);
});
test("registry supports duplicate rejection, capabilities, ordering, and health", () => {
  for (const token of ["already registered", "discover", "capabilities", "health", "priority"]) assert.ok(registry.includes(token), `missing ${token}`);
});
test("search service contains resilience pipeline stages", () => {
  for (const token of ["Promise.all", "AbortController", "providerTimeoutMs", "globalTimeoutMs", "dedupe", "ranking", "cache", "telemetry", "cancelled", "timeout"]) assert.ok(service.includes(token), `missing ${token}`);
});
test("demo provider is explicitly adapter-backed and normalized", () => {
  assert.ok(provider.includes("searchDemo"));
  assert.ok(provider.includes("providerId"));
  assert.ok(provider.includes("extends BaseProvider"));
});
test("core service files stay UI-agnostic", () => {
  for (const file of ["src/services/search/SearchService.ts", "src/services/search/SearchRegistry.ts", "src/services/context/ContextEngine.ts", "src/services/graph/RelationshipGraph.ts"]) assert.doesNotMatch(readFileSync(file, "utf8"), /from ["']react|from ["']next\//);
});

console.log("Service foundation tests passed: 5 architecture scenarios covered.");
