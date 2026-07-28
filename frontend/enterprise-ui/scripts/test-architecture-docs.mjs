import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const architecture = "docs/architecture/CTV_ONE_ARCHITECTURE_V1.md";
const readme = "docs/architecture/README.md";
const specification = readFileSync(architecture, "utf8");

test("canonical architecture specification and README exist", () => {
  assert.ok(existsSync(architecture));
  assert.ok(existsSync(readme));
  assert.ok(readFileSync(readme, "utf8").includes("CTV ONE Architecture v1.0"));
});
test("all required Mermaid source diagrams exist", () => {
  for (let index = 1; index <= 10; index += 1) {
    const number = String(index).padStart(2, "0");
    assert.ok(existsSync(`docs/architecture/diagrams/${number}-${["system-context", "layered-architecture", "search-runtime", "provider-runtime", "context-runtime", "graph-runtime-current", "graph-runtime-target", "future-intelligence-runtime", "dependency-direction", "provider-extension-flow"][index - 1]}.mmd`));
  }
});
test("architecture status and boundaries are explicit", () => {
  for (const token of ["IMPLEMENTED", "PARTIALLY IMPLEMENTED", "PLANNED", "PROHIBITED DEPENDENCY", "GraphRuntimeService", "Organizational Memory", "AI Orchestrator"]) assert.ok(specification.includes(token), `missing ${token}`);
});
test("canonical documentation avoids machine-specific paths and unsupported live claims", () => {
  assert.doesNotMatch(specification, /[A-Z]:\\|C:\\Users|B:\\CTV_AI/);
  assert.ok(specification.includes("local-demo"));
});

console.log("Architecture documentation tests passed: 4 artifact and governance scenarios covered.");
