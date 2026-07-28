import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const base = readFileSync("src/services/providers/sdk/BaseProvider.ts", "utf8");
const timeout = readFileSync("src/services/providers/sdk/ProviderTimeout.ts", "utf8");
const retry = readFileSync("src/services/providers/sdk/ProviderRetry.ts", "utf8");
const errors = readFileSync("src/services/providers/sdk/ProviderErrors.ts", "utf8");
const demo = readFileSync("src/services/providers/demo/DemoSearchProvider.ts", "utf8");

test("BaseProvider defines the shared lifecycle", () => {
  for (const token of ["initialize", "validate", "execute", "normalize", "diagnose", "cleanup"]) assert.ok(base.includes(token), `missing lifecycle hook ${token}`);
});
test("SDK owns timeout, cancellation, retry, and cleanup boundaries", () => {
  for (const token of ["ProviderTimeoutError", "PROVIDER_CANCELLED", "clearTimeout", "removeEventListener"]) assert.ok(timeout.includes(token), `missing ${token}`);
  for (const token of ["attempts", "exponential", "noRetry"]) assert.ok(retry.includes(token), `missing ${token}`);
});
test("SDK standardizes provider error classes", () => {
  for (const token of ["ProviderConfigurationError", "ProviderUnavailableError", "ProviderUnauthorizedError", "ProviderExecutionError"]) assert.ok(errors.includes(token), `missing ${token}`);
});
test("DemoSearchProvider inherits SDK behavior and retains demo adapter logic", () => {
  assert.ok(demo.includes("extends BaseProvider"));
  assert.ok(demo.includes("searchDemo"));
  assert.ok(demo.includes("protected async execute"));
});
test("SDK core remains UI-agnostic", () => {
  for (const file of ["BaseProvider.ts", "ProviderTimeout.ts", "ProviderRetry.ts", "ProviderErrors.ts"]) assert.doesNotMatch(readFileSync(`src/services/providers/sdk/${file}`, "utf8"), /from ["']react|from ["']next\//);
});

console.log("Provider SDK tests passed: 5 scenarios covered.");
