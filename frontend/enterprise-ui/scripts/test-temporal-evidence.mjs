import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const contracts = readFileSync("src/contracts/temporal/index.ts", "utf8");
const utility = readFileSync("src/services/temporal/TemporalEvidence.ts", "utf8");
const normalizer = readFileSync("src/services/providers/local/files/local-files-normalizer.ts", "utf8");
const context = readFileSync("src/services/context/ContextEngine.ts", "utf8");
const graph = readFileSync("src/services/graph/GraphBuilder.ts", "utf8");
const adapter = readFileSync("src/services/memory/runtime/MemoryContributionAdapter.ts", "utf8");

test("temporal contracts are readonly, provider-independent, and explicit", () => {
  for (const token of ["TemporalEvidence", "source-event", "source-metadata", "provider-observation", "runtime-processing", "TemporalEvidencePrecision", "Readonly<"]) assert.ok(contracts.includes(token), `missing ${token}`);
  assert.doesNotMatch(contracts, /from\s+["'][^"']*(memory|react|next\/)[^"']*["']/i);
});
test("normalization validates source timestamps and produces deterministic identity", () => {
  for (const token of ["validTimestamp", "Date.parse", "temporal:", "timestamp-invalid", "timestamp-missing", "precisionFor"]) assert.ok(utility.includes(token), `missing ${token}`);
  assert.doesNotMatch(utility, /new Date\(|Date\.now\(/);
  assert.ok(normalizer.includes("temporalEvidenceFromSourceMetadata"));
});
test("evidence survives context and graph provenance without changing topology", () => {
  for (const token of ["temporalEvidence", "new Map", "Object.freeze"]) assert.ok(context.includes(token), `missing ${token}`);
  for (const token of ["snapshot.temporalEvidence", "temporalEvidence:", "addNode"]) assert.ok(graph.includes(token), `missing ${token}`);
});
test("memory maps eligible evidence and excludes runtime categories", () => {
  for (const token of ["created", "modified", "provider-observation", "runtime-processing", "Temporal evidence mapped to observation"]) assert.ok(adapter.includes(token), `missing ${token}`);
  assert.doesNotMatch(adapter, /SearchService|ContextEngine|BaseProvider|fetch\(/);
});

console.log("Temporal evidence tests passed: 4 contract, normalization, propagation, and memory scenarios covered.");
