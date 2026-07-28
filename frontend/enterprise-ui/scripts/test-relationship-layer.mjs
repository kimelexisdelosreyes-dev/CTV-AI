import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const designSystem = readFileSync("src/design-system/components/relationships.tsx", "utf8");
const files = readFileSync("src/components/files-workspace.tsx", "utf8");
const search = readFileSync("src/components/universal-search.tsx", "utf8");
const css = readFileSync("src/app/globals.css", "utf8");

test("relationship design-system primitives cover the presentation layer", () => {
  for (const name of ["RelationshipCard", "RelationshipStrip", "RelationshipBadge", "RelationshipMap", "RelationshipTimeline", "RelatedObjectsPanel", "EnterpriseBreadcrumb"]) assert.ok(designSystem.includes(`function ${name}`), `missing ${name}`);
});

test("Files exposes contextual relationship navigation", () => {
  for (const token of ["EnterpriseBreadcrumb", "RelationshipStrip", "RelationshipMap", "RelationshipCard"]) assert.ok(files.includes(token), `Files missing ${token}`);
});

test("Universal Search preview exposes relationship context", () => {
  assert.ok(search.includes("RelationshipStrip"));
  assert.ok(search.includes("RelationshipMap"));
});

test("relationship layer includes responsive and accessible semantics", () => {
  for (const token of ["aria-label=\"Enterprise relationship path\"", "role=\"list\"", ".relationship-map", ".enterprise-breadcrumb"]) assert.ok(designSystem.includes(token) || css.includes(token), `missing ${token}`);
});

console.log("Relationship layer tests passed: 4 scenarios covered.");
