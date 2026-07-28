import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const adapter = readFileSync(new URL("../src/demo/adapters/experience.ts", import.meta.url), "utf8");
const data = readFileSync(new URL("../src/demo/data/experience.ts", import.meta.url), "utf8");
const guide = readFileSync(new URL("../src/components/executive-demo-guide.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/design-system/design-system.css", import.meta.url), "utf8");
const tokens = readFileSync(new URL("../src/design-system/tokens/tokens.css", import.meta.url), "utf8");

test("experience layer includes reduced-motion-safe motion primitives", () => {
  for (const className of ["ctv-route-transition", "ctv-stagger", "ctv-overlay", "ctv-enterprise-map"]) {
    assert.match(styles, new RegExp(className));
  }
  assert.match(styles, /prefers-reduced-motion:\s*reduce/);
});

test("motion duration tokens include sprint 2.3 timing language", () => {
  for (const token of ["--ctv-motion-instant", "--ctv-motion-fast", "--ctv-motion-search", "--ctv-motion-emphasized"]) {
    assert.match(tokens, new RegExp(`${token}:`));
  }
});

test("sprint 3.0 demo dataset uses one connected executive story", () => {
  for (const phrase of [
    "Caloocan Fire Documentary",
    "Interview_Lee_1987.mov",
    "FireStation_Archive_1978.tif",
    "Alibaba OSS",
    "Studio Marketing Campaign",
  ]) {
    assert.match(data, new RegExp(phrase));
  }
});

test("executive guide preserves the required guided demonstration path", () => {
  for (const phrase of [
    "Start in Workspace",
    "Search Lee Chin interview",
    "Inspect Enterprise File Discovery",
    "Verify Organizational Memory",
    "Ask My AI",
    "Trace Enterprise Infrastructure",
    "Return to Workspace",
  ]) {
    assert.match(guide, new RegExp(phrase));
  }
});

test("demo adapters are isolated and expose scenario states", () => {
  for (const symbol of ["searchDemo", "sourceActivityForScenario", "fileDiscoveryDemo", "enterpriseMapDemo", "dedupeNotifications"]) {
    assert.match(adapter, new RegExp(`function ${symbol}`));
  }
  for (const scenario of ["success", "partial", "offline", "error"]) {
    assert.match(adapter, new RegExp(`"${scenario}"`));
  }
});
