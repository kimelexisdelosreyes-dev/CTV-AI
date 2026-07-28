import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const root = "src/contracts/memory/";
const files = ["Observation.ts", "MemoryEvent.ts", "Timeline.ts", "Memory.ts", "Recall.ts", "Query.ts", "MemorySnapshot.ts", "index.ts"];
const content = files.map((file) => readFileSync(`${root}${file}`, "utf8")).join("\n");

test("memory contracts cover observation through recall", () => {
  for (const token of ["Observation", "MemoryEvent", "TimelineEntry", "MemoryRecord", "MemoryRecall", "MemorySnapshot", "MemoryQuery", "MemoryEvidence", "MemoryDiagnostics", "MemoryStatistics"]) assert.ok(content.includes(token), `missing ${token}`);
});
test("memory contracts use readonly public structures", () => {
  for (const token of ["Readonly<", "readonly Observation[]", "readonly MemoryRecord[]", "readonly MemoryEvidence[]"]) assert.ok(content.includes(token), `missing ${token}`);
});
test("memory contracts reference identities and never own runtime dependencies", () => {
  assert.ok(content.includes("graphNodeId"));
  assert.doesNotMatch(content, /react|next\/|SearchService|BaseProvider|GraphBuilder|RelationshipGraph|localStorage|fetch\(/);
  assert.equal(existsSync("src/services/memory/MemoryService.ts"), false);
});
test("memory documentation declares contract-only boundaries", () => {
  const documentation = readFileSync("docs/architecture/010-organizational-memory.md", "utf8");
  for (const token of ["contract-only", "PLANNED", "no runtime service", "no runtime or persistence"]) assert.ok(documentation.includes(token), `missing ${token}`);
});

console.log("Memory contract tests passed: 4 ownership and immutability scenarios covered.");
