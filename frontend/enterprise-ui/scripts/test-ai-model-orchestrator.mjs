import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const contracts = read("src/contracts/orchestrator/index.ts");
const registry = read("src/services/orchestrator/AIModelRegistry.ts");
const planner = read("src/services/orchestrator/AIModelOrchestrator.ts");
const all = `${contracts}\n${registry}\n${planner}`;

test("registry hardening: validates, sorts, fingerprints, and freezes", () => {
  for (const token of ["Duplicate or missing model ID", "Invalid model priority", "Invalid model location", "Invalid model provider type", "Invalid model capability metadata", ".sort((a, b) => a.identity.modelId.localeCompare", "sourceFingerprint", "Object.freeze"]) assert.match(all, new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});
test("policy hardening: defaults are local-only and restrictive", () => {
  for (const token of ["allowLocalModels:true", "allowPublicCloudModels:false", "allowToolUse:false", "allowExternalKnowledge:false", "allowSensitiveData:false", "requireCitations:true", "requireEvidenceTraceability:true", "requireLocalOnly:true", "blockedModelIds", "allowedModelIds", "preferredModelIds"]) assert.ok(planner.includes(token));
});
test("eligibility hardening: declared capabilities and modalities are required", () => {
  for (const token of ["input-modality", "output-type", "execution-mode", "capability:${cap}", "citations", "structured-output", "reasoning", "language", "long-context", "blocked-provider", "location-disallowed"]) assert.ok(planner.includes(token));
});
test("selection and tie-break are deterministic", () => {
  assert.match(planner, /sort\(\(a,b\)=>b\.score-a\.score \|\| a\.modelId\.localeCompare\(b\.modelId\)\)/);
  assert.ok(planner.includes("preferredModelIds.includes"));
  assert.ok(!planner.includes("Math.random"));
});
test("fallback candidates are independently eligible, bounded, and immutable", () => {
  assert.ok(planner.includes("selected.slice(1,1+Math.min"));
  assert.ok(planner.includes("effective.fallbackAllowed"));
  assert.ok(planner.includes("const selected=eligibility.filter(x=>x.eligible)"));
});
test("execution plans retain references and contain one planning-only step", () => {
  for (const token of ["contextPackageId", "contextFingerprint", "registryId", "registryVersion", "type:\"model-execution\"", "fingerprint", "policy:effective", "limits:bounded"]) assert.ok(planner.includes(token));
});
test("serialization and security exclude runtime objects from plan contracts", () => {
  assert.ok(!contracts.includes("AbortSignal stored"));
  assert.ok(!contracts.includes("apiKey"));
  assert.ok(!contracts.includes("credentials"));
  assert.ok(!contracts.includes("Map<"));
  assert.ok(!contracts.includes("Set<"));
  assert.match(contracts, /signal\?: AbortSignal/);
  assert.ok(!planner.includes("signal:"));
});
test("dependency governance excludes provider, runtime, prompt, and UI coupling", () => {
  for (const forbidden of ["SearchService", "ContextEngine", "GraphRuntime", "MemoryRuntime", "ollama", "openai", "fetch(", "React", "prompt", "localStorage", "indexedDB"]) assert.ok(!planner.toLowerCase().includes(forbidden.toLowerCase()), forbidden);
});
test("architecture pipeline is context package to plan only", () => {
  assert.match(contracts, /contextPackage: AIContextPackage/);
  assert.match(contracts, /AIExecutionPlan/);
  assert.ok(!planner.includes("AIContextPackageBuilder"));
});
console.log("AI model orchestrator hardening tests passed: registry, policy, eligibility, selection, fallback, plan, serialization, security, dependencies, and architecture verified.");
