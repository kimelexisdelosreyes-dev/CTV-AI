# P2.7 Release Stabilization, Test-Suite Repair and CI Baseline

## Original failures and root causes

The starting backend result was 174 passed and five failed.

| Failure | Classification | Root cause and repair |
| --- | --- | --- |
| Version endpoint expected `1.0.0` | Stale expectation and configuration isolation | Runtime default, package metadata, test, and local `.env` disagreed. Packaging and runtime now derive from `app.core.version.APP_VERSION`. |
| Async connector test did not execute | Missing test dependency | `pytest-asyncio` was undeclared. It is now a test dependency with explicit strict mode and function-scoped loops. |
| Developer model list expected an old default | Stale expectation plus runtime mismatch | The endpoint used legacy `ollama_model`; it now uses the router's effective default helper and the test derives its expectation. |
| Benchmark expected `qwen3:14b` to be the default | Stale expectation | The test now submits the effective configured default, without hardcoding a model name. |
| OpenAI model list omitted auto/comedy | Stale registry expectation | The test now validates the intended alias registry, including `ctv-ai-auto` and all registered assistants. |

No production assertion was removed or weakened.

## Authoritative application version

`backend/app/core/version.py` is the single source. `Settings.app_version`, FastAPI/OpenAPI, `/api/v1/version`, and the root response use it. `pyproject.toml` declares its project version dynamically from the same attribute. The former `.env` version value no longer overrides release identity.

## Model-test strategy

Tests obtain default, fast, knowledge, operations, balanced, and reasoning models from settings. Router tests still verify explicit reasoning terms, context-role selection, model fallback, model availability caching, and request-content privacy. A dedicated assertion confirms prompt length alone does not select the reasoning role. Registry tests override settings with synthetic names to prove environment-driven construction.

## Async test configuration

`pytest-asyncio>=0.25,<2.0` is declared and pytest uses explicit strict mode with function-scoped event loops. The valid connector test remains asynchronous. AnyIO-based tests retain their existing backend fixture behavior. Unknown marker warnings are treated as defects rather than ignored.

## External-service isolation

`backend/tests/conftest.py` sets process-local test values before application imports. Monday and the scheduler are disabled; PostgreSQL, Ollama, and Qdrant point at a non-service loopback port. Individual tests continue to mock the service boundary they exercise. The suite therefore cannot use the developer `.env`, production PostgreSQL, Monday credentials, Ollama, or Qdrant.

## Release check

From the repository root with backend and frontend dependencies installed:

```powershell
backend\.venv\Scripts\python.exe scripts\release_check.py
```

The script runs backend pytest, compileall, `git diff --check`, single-head Alembic validation, offline migration SQL generation, frontend TypeScript checking/build, and Ruff when installed. Missing optional tools or uninstalled frontend dependencies produce explicit skip messages. Required failures propagate a non-zero exit code. It never prints environment variables or requires a live service.

## CI baseline

`.github/workflows/release-check.yml` provides isolated backend and frontend jobs. Backend CI installs declared dependencies, runs all tests and compilation, verifies exactly one migration head, and generates the full offline migration chain. Frontend CI uses `npm ci`, TypeScript, and the production build. No Monday, Ollama, Qdrant, or database service is configured.

## Artifact hygiene

Root ignore rules cover benchmark output, coverage artifacts, pytest/Python caches, logs, local databases, transient ingested uploads, temporary directories, local environment files, and local model artifacts. Existing intentional tracked reports or fixtures are not deleted by this sprint.

## Migration integrity

P2.7 does not alter migrations `0010` or `0011`. Release validation checks for exactly one source head and exercises a fresh offline upgrade through head. Live database revision checking remains an operational validation command:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
```

## Remaining warnings

FastAPI's test client emits an upstream deprecation warning about Starlette's current HTTP client compatibility layer. It does not affect application behavior or test isolation and is not broadly filtered. Alembic path handling is explicitly configured with `path_separator = os` to avoid its legacy-splitting warning.
