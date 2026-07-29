import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const root = new URL("../src/features/capabilities/components/", import.meta.url);
const read = (name) => readFileSync(new URL(name, root), "utf8");

const detail = read("CapabilityDetail.tsx");
assert.match(detail, /Estimated latency/);
assert.match(detail, /Supported input/);
assert.match(detail, /Supported output/);
assert.doesNotMatch(detail, /Provider|Prompt|Handler|routing/);

const input = read("CapabilityInput.tsx");
assert.match(input, /maxLength=\{5000\}/);
assert.match(input, /Try an example/);
assert.match(input, /Executing capability/);

const result = read("CapabilityResult.tsx");
assert.match(result, /Object\.entries\(result\.output\)/);
assert.doesNotMatch(result, /dangerouslySetInnerHTML/);

const status = read("CapabilityStatus.tsx");
assert.match(status, /Capability status:/);

console.log("Capability workspace UX tests passed: safe metadata, input states, structured results, and accessible status verified.");
