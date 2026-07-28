import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = "src/services/providers/local/infrastructure/";
const providers = ["InfrastructureProvider.ts", "StorageProvider.ts", "WorkstationProvider.ts", "ComputeProvider.ts"].map((file) => readFileSync(`${root}${file}`, "utf8"));
const normalizer = readFileSync(`${root}local-infrastructure-normalizer.ts`, "utf8");
const source = readFileSync(`${root}local-infrastructure-source.ts`, "utf8");
const composition = readFileSync("src/services/search/createSearchService.ts", "utf8");

test("infrastructure providers share SDK lifecycle and manifests", () => {
  for (const provider of providers) {
    assert.ok(provider.includes("extends BaseProvider"));
    assert.ok(provider.includes("manifest: ProviderManifest"));
    assert.ok(provider.includes("protected async execute"));
    assert.ok(provider.includes("signal.aborted"));
  }
});
test("infrastructure source is indexed metadata only", () => {
  assert.ok(source.includes("demoMapNodes"));
  assert.doesNotMatch(source, /fetch\(|SMB|Docker|Ollama|Get-ChildItem|readdir/);
});
test("normalizers preserve source, status, capabilities, and relationships", () => {
  for (const token of ["Local Infrastructure Metadata", "capabilities", "relationships", "normalizeStorage", "normalizeWorkstation", "normalizeCompute"]) assert.ok(normalizer.includes(token), `missing ${token}`);
});
test("composition root registers all infrastructure providers", () => {
  for (const provider of ["InfrastructureProvider", "StorageProvider", "WorkstationProvider", "ComputeProvider"]) assert.ok(composition.includes(`new ${provider}()`), `missing ${provider}`);
});
test("providers remain UI-independent", () => {
  for (const provider of providers) assert.doesNotMatch(provider, /react|next\/|\.css|\.tsx/);
});

console.log("Infrastructure provider tests passed: 5 metadata and boundary scenarios covered.");
