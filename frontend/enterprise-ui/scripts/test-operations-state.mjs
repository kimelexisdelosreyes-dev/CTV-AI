import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(
  new URL("../src/lib/operations-state.ts", import.meta.url),
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
const { initialOperationsState, operationsSnapshotIsStale } = await import(
  moduleUrl
);

test("initial operations state has no snapshot and default filters", () => {
  const state = initialOperationsState();

  assert.equal(state.tasks.length, 0);
  assert.equal(state.lastUpdated, null);
  assert.deepEqual(state.filters, {
    query: "",
    board: "all",
    status: "all",
    priority: "all",
  });
});

test("fresh operations snapshot does not require refetch", () => {
  const now = Date.parse("2026-07-17T00:02:00Z");
  const updated = "2026-07-17T00:01:30Z";

  assert.equal(operationsSnapshotIsStale(updated, now, 120_000), false);
});

test("stale operations snapshot refreshes in background", () => {
  const now = Date.parse("2026-07-17T00:05:00Z");
  const updated = "2026-07-17T00:01:00Z";

  assert.equal(operationsSnapshotIsStale(updated, now, 120_000), true);
});

test("missing operations snapshot is stale", () => {
  assert.equal(operationsSnapshotIsStale(null, Date.now(), 120_000), true);
});
