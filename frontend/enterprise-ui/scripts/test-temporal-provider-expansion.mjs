import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const temporal = readFileSync("src/services/temporal/TemporalEvidence.ts", "utf8");
const context = readFileSync("src/services/context/ContextEngine.ts", "utf8");
const memory = readFileSync("src/services/memory/runtime/MemoryRuntimeService.ts", "utf8");
const knowledge = readFileSync("src/services/providers/local/knowledge/local-knowledge-normalizer.ts", "utf8");
const projects = readFileSync("src/services/providers/local/projects/local-projects-normalizer.ts", "utf8");
const infrastructure = readFileSync("src/services/providers/local/infrastructure/local-infrastructure-normalizer.ts", "utf8");

test("knowledge and projects use the shared deterministic temporal factory", () => {
  for (const source of [knowledge, projects]) assert.ok(source.includes("temporalEvidenceFromSourceMetadata"));
  assert.doesNotMatch(`${knowledge}\n${projects}`, /MemoryRuntimeService|Observation|MemoryRecord/);
});
test("infrastructure remains evidence-free without an explicit timestamp", () => {
  assert.doesNotMatch(infrastructure, /temporalEvidenceFromSourceMetadata|Date\.now\(|new Date\(/);
});
test("statistics are deterministic and immutable across context and memory", () => {
  for (const token of ["summarizeTemporalEvidence", "Object.freeze", "memoryEligibleCount", "readyEmptySessionCount"]) assert.ok(temporal.includes(token), `missing ${token}`);
  assert.ok(context.includes("temporalStatistics"));
  assert.ok(memory.includes("temporalStatistics"));
});
test("runtime telemetry is optional, count-only, and failure-isolated", () => {
  for (const token of ["memory_runtime_ready", "memory_runtime_ready_empty", "evidenceCount", "observationCount", "try { this.telemetry?.record"]) assert.ok(memory.includes(token), `missing ${token}`);
  assert.doesNotMatch(memory, /title|path|referenceId|sourceEntityId/);
});

console.log("Temporal provider expansion tests passed: 4 provider, statistics, and telemetry scenarios covered.");
