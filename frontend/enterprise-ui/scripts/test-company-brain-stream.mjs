import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(
  new URL("../src/lib/api.ts", import.meta.url),
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
const { parseSseEvents, streamKnowledgeAsk } = await import(moduleUrl);

test("parses CRLF, comments, and multiple events from one chunk", () => {
  const parsed = parseSseEvents(
    ': heartbeat\r\nevent: start\r\ndata: {"request_id":"one",\r\ndata: "conversation_id":null}\r\n\r\n' +
      'event: token\r\ndata: {"text":"Visible"}\r\n\r\n',
  );

  assert.equal(parsed.remaining, "");
  assert.deepEqual(parsed.events.map((event) => event.type), ["start", "token"]);
  assert.equal(parsed.events[1].text, "Visible");
});

test("keeps an event split across network chunks until complete", () => {
  const first = parseSseEvents('event: token\ndata: {"text":');
  assert.equal(first.events.length, 0);

  const second = parseSseEvents(first.remaining + '"Split"}\n\n');
  assert.equal(second.events.length, 1);
  assert.equal(second.events[0].text, "Split");
});

test("flushes a final complete event without a trailing blank line", () => {
  const parsed = parseSseEvents(
    'event: done\ndata: {"answer_chars":7,"first_token_latency_ms":1,"duration_ms":2}',
    true,
  );
  assert.equal(parsed.events[0].type, "done");
});

test("parses progressive Company Brain SSE token and done events", async () => {
  const originalFetch = globalThis.fetch;
  const encoder = new TextEncoder();
  globalThis.fetch = async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode(
              'event: start\ndata: {"request_id":"request-1","conversation_id":null}\n\n' +
                'event: token\ndata: {"text":"Visible"}\n\n' +
                'event: token\ndata: {"text":" answer"}\n\n' +
                'event: done\ndata: {"answer_chars":14,"first_token_latency_ms":20,"duration_ms":40}\n\n',
            ),
          );
          controller.close();
        },
      }),
      { status: 200 },
    );

  const events = [];
  try {
    await streamKnowledgeAsk({ question: "ignored" }, (event) => events.push(event));
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(events.map((event) => event.type), [
    "start",
    "token",
    "token",
    "done",
  ]);
  assert.equal(events[1].text + events[2].text, "Visible answer");
});
