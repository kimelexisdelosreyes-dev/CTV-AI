# Backend Runtime Integration & Controlled Cutover

## Status

Python AI Runtime and the Python Ollama Adapter are production-integrated behind `CTV_ONE_AI_RUNTIME_ENABLED`. The default production path is legacy when the flag is absent or false. The runtime path is available only when `CTV_ONE_AI_RUNTIME_ENABLED=true`. Roll back by setting the flag false and restarting the backend.

## Architecture and compatibility

`/chat` remains unchanged: `chat.py -> AIRouter.chat`. AIRouter still builds the system/user messages, invokes Atlas shadow routing, and remains the sole owner of that prompt flow. In legacy mode it calls `ollama_service.chat(messages)` exactly as before. In runtime mode it copies the already-built, already-routed messages into immutable `RuntimeMessage` values, copies the existing default selected model ID into a narrow `ExecutionPlan`, and calls `AIModelRuntime -> OllamaModelAdapter -> ExistingOllamaServiceTransport -> ollama_service.chat`.

The composition root is `app.ai_runtime.composition.build_local_ollama_runtime`. It uses the existing Ollama service, builds the transport, adapter, registry, and runtime locally, and performs no import-time network, health, or model-inventory work. AIRouter caches this runtime per router instance after the flag-enabled path is first used.

No prompt wording, roles, order, whitespace, system messages, history, routing decision, API route, request/response contract, authentication, or frontend code changes. The current live chat path relies on the Ollama service default model; that exact effective model is copied into the runtime plan. The current chat path has no retry or fallback, so the runtime plan is zero retries and zero fallbacks. Its timeout is the existing `request_timeout_seconds`; effective transport/runtime timing cannot exceed that value.

## Errors, cancellation, and trace safety

Runtime results are translated back to the existing `OllamaServiceError` family before reaching the route. Runtime failure never invokes the legacy path, avoiding duplicate generation. Cancellation is cooperative: outer task cancellation cancels the runtime-owned adapter task; the adapter checks before and after transport. `ollama_service.py` has no cancellation token or explicit provider abort operation, so provider-side in-flight generation termination is not guaranteed.

The runtime path emits a log-only immutable execution trace containing IDs, selected model, adapter/provider/location, duration, status, finish reason, counters, and sanitized diagnostic codes. It excludes prompts, messages, context, credentials, endpoints, provider payloads, response bodies, and tracebacks. No trace persistence or database state is added.

## Parity gate

Required cutover parity is implemented: ordered provider-neutral message handling, selected-model preservation, no retries/fallbacks, effective timeout parity, response text translation, safe error conversion, and cooperative cancellation. TypeScript-only plan-policy/source-staleness validation, progress statuses, structured outputs/errors, advanced limits, and richer registry/result fingerprints are not used by the current chat execution (deferred future capabilities). Python's compact tuple metadata/diagnostics representation is intentional.

## Validation and operations

Focused tests cover flag absence/false, enabled routing, exact payload/model preservation, no legacy fallback, invalid setting validation, and request isolation. Use `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_backend_runtime_cutover.py`.

For local activation only, set `CTV_ONE_AI_RUNTIME_ENABLED=true` in the shell/session, restart the backend, call health and `/chat`, and compare the unchanged API response. Set it to `false` and restart to roll back. Do not overwrite `.env`. If no local Ollama server is available, use mocked integration evidence only; no live-model claim should be made. Production-wide activation requires separate authorization.
