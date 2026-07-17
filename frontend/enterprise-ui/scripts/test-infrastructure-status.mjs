import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const source = await readFile(
  new URL("../src/lib/infrastructure-status.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
});
const moduleUrl = `data:text/javascript;base64,${Buffer.from(
  compiled.outputText,
).toString("base64")}`;
const { displayText, normalizeInfrastructureStatus } = await import(moduleUrl);

test("normalizes structured embedding readiness", () => {
  const rows = normalizeInfrastructureStatus({
    postgresql: "healthy",
    qdrant: "healthy",
    embedding: {
      status: "healthy",
      category: "ready",
      model: "qwen3:8b",
    },
  });

  const embedding = rows.find((row) => row.key === "embedding");
  assert.equal(embedding.status, "healthy");
  assert.equal(embedding.category, "ready");
  assert.equal(embedding.model, "qwen3:8b");
  assert.equal(embedding.isHealthy, true);
});

test("uses fallback for missing model", () => {
  const rows = normalizeInfrastructureStatus({
    embedding: {
      status: "healthy",
      category: "ready",
    },
  });

  assert.equal(rows.find((row) => row.key === "embedding").model, "Unknown");
});

test("renders null infrastructure as unknown service rows", () => {
  const rows = normalizeInfrastructureStatus(null);

  assert.equal(rows.length, 3);
  assert.equal(rows.every((row) => row.status === "Unknown"), true);
});

test("handles partial infrastructure response", () => {
  const rows = normalizeInfrastructureStatus({ qdrant: "healthy" });

  assert.equal(rows.find((row) => row.key === "qdrant").status, "healthy");
  assert.equal(rows.find((row) => row.key === "postgresql").status, "Unknown");
});

test("marks unavailable service as not healthy", () => {
  const rows = normalizeInfrastructureStatus({
    postgresql: "unavailable",
  });

  const postgresql = rows.find((row) => row.key === "postgresql");
  assert.equal(postgresql.status, "unavailable");
  assert.equal(postgresql.isHealthy, false);
});

test("does not render raw objects or object stringification", () => {
  assert.equal(displayText({ status: "healthy" }), "Unknown");
  assert.equal(displayText(["secret-token"]), "Unknown");
});

test("normalized values can render as React children", () => {
  const rows = normalizeInfrastructureStatus({
    embedding: {
      status: "healthy",
      category: "ready",
      model: "qwen3:8b",
    },
  });
  const embedding = rows.find((row) => row.key === "embedding");

  assert.doesNotThrow(() => {
    renderToStaticMarkup(React.createElement("b", null, embedding.status));
  });
});
