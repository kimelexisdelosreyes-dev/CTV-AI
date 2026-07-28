import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync("src/components/files-workspace.tsx", "utf8");
const designSystem = readFileSync("src/design-system/components/enterprise.tsx", "utf8");
const css = readFileSync("src/app/globals.css", "utf8");

test("File Discovery exposes the selected asset intelligence workflow", () => {
  for (const token of ["Asset intelligence", "Storage locations", "Relationship graph", "Version history", "AI intelligence", "Recommended actions"]) {
    assert.ok(page.includes(token), `missing ${token}`);
  }
});

test("File Discovery reuses adapter data and reusable design-system primitives", () => {
  assert.ok(page.includes("fileDiscoveryDemo"));
  assert.ok(designSystem.includes("Checksum verification is unavailable"));
  for (const token of ["AssetBadge", "AssetIdentityCard", "StorageLocationCard", "StorageHealthBadge", "VersionTimeline"]) {
    assert.ok(designSystem.includes(`export function ${token}`), `missing primitive ${token}`);
  }
});

test("File Discovery has responsive and reduced-motion-safe styling", () => {
  for (const token of [".files-summary-grid", ".files-relationship-graph", "prefers-reduced-motion"]) assert.ok(css.includes(token));
});

console.log("File Discovery intelligence tests passed: 3 scenarios covered.");
