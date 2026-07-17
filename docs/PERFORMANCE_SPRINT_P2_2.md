# Performance Sprint P2.2: Streaming Response Engine

## Endpoint

`POST /api/v1/knowledge/ask/stream` is an authenticated Server-Sent Events
endpoint. Its JSON body is the same as `POST /api/v1/knowledge/ask`, including
the optional `conversation_id`. The existing non-streaming endpoint is unchanged.

The stream exposes only these event types:

- `start`: request and conversation identifiers.
- `context_ready`: selected context component names and total retrieval time.
- `token`: visible assistant text from Ollama only.
- `done`: answer size, first-token latency, and total duration.
- `error`: a safe error category and safe detail.

Prompts, source text, employee context, connector payloads, tokens, and stack
traces are never included in the event payloads.

## Runtime behavior

Routing, parallel retrieval, budgeting, and prompt assembly run before
`context_ready`. Ollama is then called with `/api/chat`, `stream: true`, the
configured `think` setting, and the existing `num_predict` option. Only
`message.content` is emitted. Thinking content is ignored. Malformed, upstream,
timeout, empty, and truncation failures produce controlled safe errors.

First-token latency is measured from the start of the Ollama streaming request to
the first non-empty visible assistant chunk. It is `null` when no model token is
received. Streaming metrics include response mode, context-ready offset,
inference-start offset, first-token latency, chunk count, answer characters,
completion/cancellation state, error category, and persistence state.

## Conversation persistence

The user message is saved before preparation. The server accumulates only visible
assistant content and saves it after a successful completed stream. A failed or
cancelled stream does not save a partial assistant response. This keeps history
free of incomplete model output; the already-visible partial response remains in
the current browser panel until it is refreshed.

## Frontend behavior

Company Brain adds the user message and an empty assistant placeholder locally,
then updates the placeholder for each `token` event. It shows preparation and
generation states, exposes Stop while active, refreshes Recents on completion,
and uses the existing `/knowledge/ask` request only when the streaming request
fails before the stream starts.

## Manual check

1. Open Company Brain and ask a policy or operations question.
2. Confirm the user message and assistant placeholder appear immediately.
3. Confirm text grows before the full response has completed.
4. Confirm the completed conversation appears in Recents and survives refresh.
5. Use Stop during a response and confirm no new partial assistant entry appears
   after reloading the conversation.
