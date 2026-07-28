# Python Ollama Adapter

Phase 4.7C.2B adds an isolated backend Ollama adapter. It wraps the existing `ollama_service.chat` transport rather than changing it. The production route remains `chat.py -> ai_router.py -> ollama_service.py`, and still uses `/api/chat`, non-streaming messages, existing prompt construction, configured timeout, and existing model roles.

The adapter exposes configured CTV ONE model IDs, accepts only local synchronous Ollama requests, preserves model and content exactly, invokes transport once, and normalizes text and provider-reported token counts. Cancellation is checked before/after transport; in-flight cancellation is limited by the current service API. Runtime retains retry, fallback, and timeout ownership. No live Ollama is needed for mock-based tests, and no cutover occurs in this phase.
