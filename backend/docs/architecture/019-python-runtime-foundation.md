# Python AI Runtime Foundation

Phase 4.7C.2A ports the TypeScript runtime architecture into the FastAPI backend as a provider-independent, frozen-dataclass foundation. It validates immutable execution plans, resolves private adapters deterministically, and executes only the primary model and preplanned fallbacks with bounded retries and timeout/cancellation handling.

It is integrated with the chat execution boundary behind the default-off `CTV_ONE_AI_RUNTIME_ENABLED` flag. The production default remains the legacy `/api/chat` Ollama service path, while the included deterministic test adapter performs no network work.

Phase 4.7C.2B adds an isolated Python Ollama adapter beneath this foundation. Its controlled production cutover is provided by Phase 4.7C.2C.

Phase 4.7C.2C production-integrates this foundation behind the default-off `CTV_ONE_AI_RUNTIME_ENABLED` flag. See `021-backend-runtime-cutover.md` for activation and rollback.

## Phase 4.7C.2B.1 hardening

### Message contract and conversation fidelity

`RuntimeRequest` is an immutable runtime input carrying a non-empty `tuple[RuntimeMessage, ...]`. A message has exactly the provider-neutral `role` (`system`, `user`, or `assistant`) and string `content` fields. Tuple-only input prevents collection mutation; frozen messages prevent turn mutation; role and content types are validated. `RuntimeRequest.to_dict()` and `RuntimeMessage.to_dict()` are JSON-safe, and `RuntimeResult.to_dict()` serializes a result without retaining request messages.

The runtime neither sorts, combines, nor creates conversation turns. It passes its tuple unchanged to the adapter. The Ollama adapter maps each turn once to the service's `{role, content}` shape in the same order. Mock tests cover `system → user → assistant → user → assistant` exactly.

### TypeScript parity verification

The Python foundation matches the TypeScript reference for deterministic adapter resolution, primary-then-preplanned-fallback lifecycle, bounded retry behavior, timeout/fallback decisions, terminal cancellation, immutable result records, attempt diagnostics, metadata, and serialization support.

Intentional differences are documented rather than hidden: Python is a deliberately smaller foundation. It has no TS plan-policy/source-staleness validation, lifecycle-progress statuses (`validating`, `resolving-adapter`, `executing`, `retrying`, `falling-back`), wall-clock durations, result fingerprint, registry ID/source fingerprint, maximum-attempt/output limits, or structured output/error objects. Its diagnostics are stable string codes and its metadata is immutable key/value tuples. These differences are outside the current feature-gated chat execution scope.

### Cancellation and development environment

Cancellation is checked before adapter resolution, raced cooperatively against an active adapter call, propagated by cancelling the runtime-owned adapter task, and checked by the Ollama adapter both before and after transport. `ollama_service.py` exposes no cancellation token or explicit request-abort API; therefore the adapter cannot guarantee provider-side in-flight cancellation independently of task cancellation. The existing transport is intentionally not rewritten.

Run tests with the project environment: `backend/.venv/Scripts/python.exe -m pytest`. Required development dependencies are declared in `backend/requirements.txt`, including `pytest`, `pytest-asyncio`, and `pydantic-settings`; the checked virtual environment currently provides Python 3.12, pytest 8.4.2, and pydantic-settings 2.14.2.
