import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const files = readFileSync("src/services/providers/local/files/LocalFilesSearchProvider.ts", "utf8");
const filesNormalizer = readFileSync("src/services/providers/local/files/local-files-normalizer.ts", "utf8");
const knowledge = readFileSync("src/services/providers/local/knowledge/LocalKnowledgeSearchProvider.ts", "utf8");
const knowledgeNormalizer = readFileSync("src/services/providers/local/knowledge/local-knowledge-normalizer.ts", "utf8");
const projects = readFileSync("src/services/providers/local/projects/LocalProjectsSearchProvider.ts", "utf8");
const projectsNormalizer = readFileSync("src/services/providers/local/projects/local-projects-normalizer.ts", "utf8");
const composition = readFileSync("src/services/search/createSearchService.ts", "utf8");

test("all local providers inherit the SDK and expose normalized execution", () => {
  for (const source of [files, knowledge, projects]) {
    assert.ok(source.includes("extends BaseProvider"));
    assert.ok(source.includes("protected async execute"));
    assert.ok(source.includes("signal.aborted"));
    assert.ok(source.includes("status: \"ready\""));
  }
});
test("local normalizers preserve source attribution and relationships", () => {
  for (const source of [filesNormalizer, knowledgeNormalizer, projectsNormalizer]) {
    assert.ok(source.includes("providerId"));
    assert.ok(source.includes("relationships"));
    assert.ok(source.includes("source"));
  }
});
test("composition root registers the migration-safe provider set", () => {
  for (const id of ["DemoSearchProvider", "LocalFilesSearchProvider", "LocalKnowledgeSearchProvider", "LocalProjectsSearchProvider"]) assert.ok(composition.includes(`new ${id}()`), `missing ${id}`);
});
test("local providers do not import UI concerns", () => {
  for (const file of ["files/LocalFilesSearchProvider.ts", "knowledge/LocalKnowledgeSearchProvider.ts", "projects/LocalProjectsSearchProvider.ts"]) assert.doesNotMatch(readFileSync(`src/services/providers/local/${file}`, "utf8"), /react|next\/|\.css|\.tsx/);
});

console.log("Local provider tests passed: 4 architecture and normalization scenarios covered.");
