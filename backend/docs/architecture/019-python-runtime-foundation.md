# Python AI Runtime Foundation

Phase 4.7C.2A ports the TypeScript runtime architecture into the FastAPI backend as a provider-independent, frozen-dataclass foundation. It validates immutable execution plans, resolves private adapters deterministically, and executes only the primary model and preplanned fallbacks with bounded retries and timeout/cancellation handling.

It is not connected to `chat.py`, `ai_router.py`, or `ollama_service.py`. The production route continues to use the legacy `/api/chat` Ollama service and its existing prompt construction. The included deterministic test adapter performs no network work. A Python Ollama adapter and controlled production cutover remain future phases.

Phase 4.7C.2B adds an isolated Python Ollama adapter beneath this foundation. Production runtime cutover remains not implemented.
