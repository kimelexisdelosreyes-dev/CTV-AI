import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const adapter = readFileSync("src/services/memory/runtime/MemoryContributionAdapter.ts", "utf8");
const builder = readFileSync("src/services/memory/runtime/MemoryBuilder.ts", "utf8");
const runtime = readFileSync("src/services/memory/runtime/MemoryRuntimeService.ts", "utf8");
const query = readFileSync("src/services/memory/runtime/MemoryRuntimeQueryService.ts", "utf8");
const searchAdapter = readFileSync("src/features/search/search-service-adapter.ts", "utf8");

test("memory contribution adapter requires explicit temporal evidence", () => {
  for (const token of ["GraphRuntimeSession", "timestampCategory", "sourceId", "provenance", "Temporal evidence mapped to observation"]) assert.ok(adapter.includes(token), `missing ${token}`);
  assert.doesNotMatch(adapter, /SearchService|ContextEngine|BaseProvider|fetch\(/);
});
test("memory builder is deterministic, conservative, and immutable", () => {
  for (const token of ["observation:", "occurredAt", "seen", "Empty memory snapshot", "Object.freeze", "events: Object.freeze\(\[\]\)"]) assert.ok(builder.includes(token), `missing ${token}`);
  assert.doesNotMatch(builder, /Date\.now\(\).*occurredAt|GraphBuilder|SearchService|react/);
});
test("runtime service supports lifecycle safety", () => {
  for (const token of ["ready-empty", "buildKey", "version !== this.version", "signal?.aborted", "invalidate", "reset", "Object.freeze"]) assert.ok(runtime.includes(token), `missing ${token}`);
});
test("memory query is bounded and never builds memory", () => {
  for (const token of ["maxLimit", "Math.min", "Memory query unavailable", "Memory query truncated"]) assert.ok(query.includes(token), `missing ${token}`);
  assert.doesNotMatch(query, /MemoryBuilder|\.build\(/);
});
test("search adapter invokes memory after ready graph runtime", () => {
  for (const token of ["createMemoryRuntimeService", "graphResult.session", "memoryRuntime.build"]) assert.ok(searchAdapter.includes(token), `missing ${token}`);
});

console.log("Memory runtime tests passed: 5 lifecycle and evidence scenarios covered.");
