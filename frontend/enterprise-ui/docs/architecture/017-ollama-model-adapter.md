# Ollama Model Adapter

Phase 4.7C.1 adds `OllamaModelAdapter` in isolation. The UI workspace audit found no Ollama request client: it only contains presentation of backend Ollama timing fields. Consequently, no legacy UI or backend inference path was changed.

The adapter uses injected configuration and fetch, calls Ollama's non-streaming `/api/generate` endpoint, and preserves the selected model ID. It accepts only local synchronous Ollama models listed in its injected configuration. Request translation uses provider-neutral `inputText` or bounded system/user/assistant messages; it does not compose enterprise prompts, route models, retry, or choose fallbacks.

Successful responses normalize text, optional JSON-object structured output, finish reason, and provider-reported token counts. HTTP/transport/empty/malformed responses are mapped to bounded controlled errors. The base URL, fetch implementation, request body, raw response, and error details are not retained in descriptors or results. Runtime cancellation is passed to fetch; runtime remains the timeout, retry, and fallback owner.

The adapter is testable with mocked fetch and is not registered in, or connected to, production execution. **Ollama adapter implemented in isolation; production runtime cutover is not implemented.** Prompt composition and streaming remain planned.
