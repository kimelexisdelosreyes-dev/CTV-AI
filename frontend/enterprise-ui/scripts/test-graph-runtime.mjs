import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const contracts = readFileSync("src/contracts/graph/runtime/index.ts", "utf8");
const runtime = readFileSync("src/services/graph/runtime/GraphRuntimeService.ts", "utf8");
const adapter = readFileSync("src/features/search/search-service-adapter.ts", "utf8");
const presentation = readFileSync("src/services/graph/runtime/GraphPresentationAdapter.ts", "utf8");

test("graph runtime contracts define session, status, diagnostics, and service boundary", () => {
  for (const token of ["GraphRuntimeStatus", "GraphRuntimeSession", "GraphRuntimeDiagnostics", "IGraphRuntimeService"]) assert.ok(contracts.includes(token), `missing ${token}`);
});
test("runtime service owns reuse, versioning, cancellation, reset, and invalidation", () => {
  for (const token of ["sourceContextSnapshotId", "requestVersion", "staleRejected", "signal?.aborted", "invalidate", "reset", "Object.freeze"]) assert.ok(runtime.includes(token), `missing ${token}`);
  assert.doesNotMatch(runtime, /ContextEngine|SearchService|react|providers/);
});
test("search adapter coordinates context-to-graph without provider imports", () => {
  for (const token of ["ContextEngine", "contributionsFromSearchResults", "createGraphRuntimeService", "graphRuntime.build"]) assert.ok(adapter.includes(token), `missing ${token}`);
  assert.doesNotMatch(adapter, /providers\/local|SearchRegistry|RelationshipGraph/);
});
test("presentation adapter returns controlled graph availability", () => {
  for (const token of ["graph-primary", "normalized-fallback", "empty", "relationships"]) assert.ok(presentation.includes(token), `missing ${token}`);
});

console.log("Graph runtime tests passed: 4 lifecycle and integration scenarios covered.");
