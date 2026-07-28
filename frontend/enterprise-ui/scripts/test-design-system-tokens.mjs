import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const css = readFileSync(new URL("../src/design-system/tokens/tokens.css", import.meta.url), "utf8");
const tokens = readFileSync(new URL("../src/design-system/tokens/index.ts", import.meta.url), "utf8");

test("semantic surface tokens are defined once in the token layer", () => {
  for (const token of [
    "--ctv-background-app",
    "--ctv-background-sidebar",
    "--ctv-background-panel",
    "--ctv-background-card",
    "--ctv-background-elevated",
    "--ctv-border-focus",
    "--ctv-text-primary",
  ]) {
    assert.match(css, new RegExp(`${token}:`));
  }
});

test("module accents and status tokens are exported for components", () => {
  for (const token of [
    "workspace",
    "aiStudio",
    "knowledge",
    "files",
    "projects",
    "myAi",
    "operations",
    "healthy",
    "processing",
    "warning",
    "critical",
    "offline",
  ]) {
    assert.match(tokens, new RegExp(`${token}:`));
  }
});

test("reduced motion is supported by shared styles", () => {
  const styles = readFileSync(new URL("../src/design-system/design-system.css", import.meta.url), "utf8");
  assert.match(styles, /prefers-reduced-motion:\s*reduce/);
});

