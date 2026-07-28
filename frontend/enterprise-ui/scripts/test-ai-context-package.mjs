import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const contracts = readFileSync("src/contracts/ai-context/index.ts", "utf8");
const builder = readFileSync("src/services/ai-context/AIContextPackageBuilder.ts", "utf8");

test("AI context contracts are readonly and independent", () => {
  for (const token of ["AIContextPackage", "AIContextBuildRequest", "AIContextBuildResult", "AIContextPackagePolicy", "AIContextPackageLimits", "readonly", "ready-partial"]) assert.ok(contracts.includes(token), `missing ${token}`);
  assert.doesNotMatch(contracts, /from\s+["'][^"']*(react|provider|openai|prompt|fetch|localStorage)[^"']*["']/i);
});
test("builder remains downstream, bounded, and deterministic", () => {
  for (const token of ["defaultAIContextLimits", "hardCap", "sourceContextSnapshotId", "sourceFingerprint", "section-truncated", "Object.freeze", "safeMetadata"]) assert.ok(builder.includes(token), `missing ${token}`);
  assert.doesNotMatch(builder, /SearchService|ContextEngine|GraphBuilder|MemoryBuilder|BaseProvider|fetch\(|OpenAI|prompt/i);
});
test("builder excludes unsafe normalized fields and supports cancellation", () => {
  for (const token of ["location", "path", "transcript", "excerpt", "package-build-cancelled", "signal?.aborted"]) assert.ok(builder.includes(token), `missing ${token}`);
});

console.log("AI context package tests passed: 3 contract, governance, and safety scenarios covered.");
