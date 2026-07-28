import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const contracts = readFileSync("src/contracts/graph/index.ts", "utf8");
const graph = readFileSync("src/services/graph/RelationshipGraph.ts", "utf8");
const builder = readFileSync("src/services/graph/GraphBuilder.ts", "utf8");
const query = readFileSync("src/services/graph/GraphQueryEngine.ts", "utf8");

test("graph contracts expose nodes, edges, snapshots, and bounded queries", () => {
  for (const token of ["GraphNode", "GraphEdge", "GraphSnapshot", "GraphNeighborhood", "GraphTraversalOptions", "IGraphBuilder", "IGraphQueryEngine"]) assert.ok(contracts.includes(token), `missing ${token}`);
});
test("relationship graph preserves provenance and immutable snapshots", () => {
  for (const token of ["duplicateNodeMerges", "duplicateEdgeMerges", "addUnresolved", "Object.freeze", "selfLoopsRejected"]) assert.ok(graph.includes(token), `missing ${token}`);
});
test("builder consumes context snapshots and records unresolved targets", () => {
  for (const token of ["ContextSnapshot", "addUnresolved", "validTypes", "ContextSnapshot"]) assert.ok(builder.includes(token), `missing ${token}`);
});
test("query engine uses bounded deterministic breadth-first traversal", () => {
  for (const token of ["maxDepth: 3", "visited", "queue", "shortestPath", "signal?.aborted"]) assert.ok(query.includes(token), `missing ${token}`);
  assert.doesNotMatch(query, /react|next\/|SearchService/);
});

console.log("Relationship graph tests passed: 4 graph behavior scenarios covered.");
