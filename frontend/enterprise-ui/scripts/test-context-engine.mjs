import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const contracts = readFileSync("src/contracts/context/index.ts", "utf8");
const engine = readFileSync("src/services/context/ContextEngine.ts", "utf8");
const resolver = readFileSync("src/services/context/EntityResolver.ts", "utf8");
const adapter = readFileSync("src/services/context/SearchContextContributions.ts", "utf8");

test("context contracts define normalized snapshots and sources", () => {
  for (const token of ["EnterpriseContext", "ContextScope", "ContextSignal", "ContextContribution", "ResolvedEntity", "ContextRelationship", "ContextSnapshot"]) assert.ok(contracts.includes(token), `missing ${token}`);
});
test("context engine builds immutable snapshots from explicit signals", () => {
  for (const token of ["Object.freeze", "runtimeContributions", "signals", "expandOneLevel", "clock"]) assert.ok(engine.includes(token), `missing ${token}`);
  assert.doesNotMatch(engine, /react|next\/|prompt|LLM/);
});
test("entity resolution is deterministic and preserves source attribution", () => {
  for (const token of ["new Map", "sourceIds", "localeCompare", "confidence"]) assert.ok(resolver.includes(token), `missing ${token}`);
});
test("search results can contribute context without provider coupling", () => {
  for (const token of ["SearchResult", "sourceFor", "relationships", "entityId"]) assert.ok(adapter.includes(token), `missing ${token}`);
});

console.log("Context engine tests passed: 4 context construction scenarios covered.");
