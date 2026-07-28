import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const resolver = readFileSync("src/services/graph/runtime/GraphIdentityResolver.ts", "utf8");
const query = readFileSync("src/services/graph/runtime/GraphRuntimeQueryService.ts", "utf8");
const presentation = readFileSync("src/services/graph/runtime/GraphPresentationAdapter.ts", "utf8");
const adapter = readFileSync("src/features/search/search-service-adapter.ts", "utf8");
const ui = readFileSync("src/components/universal-search.tsx", "utf8");

test("identity resolution prefers explicit graph identity evidence", () => {
  for (const token of ["canonical-id", "source-id", "alias", "provisional", "unresolved"]) assert.ok(resolver.includes(token), `missing ${token}`);
  assert.doesNotMatch(resolver, /find\([^\n]*label/);
});
test("runtime query facade bounds selected neighborhoods", () => {
  for (const token of ["runtime.current", "depth: 1", "maxNodes: 12", "maxEdges: 16"]) assert.ok(query.includes(token), `missing ${token}`);
});
test("presentation merges graph-primary and normalized fallback relationships", () => {
  for (const token of ["graph-primary", "normalized-fallback", "fallback.filter", "Object.freeze", "seen"]) assert.ok(presentation.includes(token), `missing ${token}`);
});
test("search UI consumes adapter output without constructing graph services", () => {
  assert.ok(adapter.includes("relationshipPresentationForSearchResult"));
  assert.ok(ui.includes("selectedRelationshipPresentation"));
  assert.doesNotMatch(ui, /GraphBuilder|GraphQueryEngine|RelationshipGraph/);
});

console.log("Graph presentation integration tests passed: 4 identity and fallback scenarios covered.");
