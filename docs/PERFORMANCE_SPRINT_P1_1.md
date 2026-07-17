# Performance Sprint P1.1

This sprint measures the current Company Brain response pipeline before any caching,
prompt compression, or retrieval optimization work.

## What Is Measured

Each `/api/v1/knowledge/ask` request emits one structured log event named
`company_brain_performance` through the `ctv_one.performance` logger.

Measured stages use seconds:

- `intelligence_router`
- `employee_context`
- `knowledge_retrieval`
- `operational_context`
- `prompt_builder`
- `ollama_total`
- `response_formatting`
- `total_request`

The authentication dependency runs before the ask handler, so this sprint does not
time authentication without changing the existing dependency contract.

Prompt metrics include character counts for the system prompt, employee context,
knowledge context, operational context, user question, and final prompt. Token counts
are estimated with the existing lightweight character-count approximation.

Ollama metrics are recorded when the local Ollama response includes them:
`prompt_eval_count`, `eval_count`, `prompt_eval_duration`, `eval_duration`,
`load_duration`, `total_duration`, and calculated tokens per second.

## Reliability Controls

P1.2 and P1.2.1 add controlled failure categories for known dependency
failures:

- `embedding_unavailable`
- `embedding_model_missing`
- `embedding_timeout`
- `embedding_endpoint_unsupported`
- `embedding_malformed_response`
- `vector_store_unavailable`
- `model_inference_timeout`
- `model_inference_unavailable`
- `model_inference_empty_response`
- `model_inference_truncated`
- `model_inference_malformed_response`
- `model_inference_upstream_error`

Known embedding and model timeout failures return safe service responses instead
of raw HTTP 500s. Successful `/api/v1/knowledge/ask` response bodies remain
unchanged; request IDs and result type are exposed through response headers.

P1.2.1 root cause: operations prompts with monday.com context used the Qwen
thinking response path. With the bounded `OLLAMA_NUM_PREDICT` budget, some
responses could spend the available generation budget in `message.thinking` and
produce no usable final `message.content`. The older validator rejected that as
`model_inference_malformed_response` before recording response structure. The
validator now records sanitized structure and classifies empty, truncated,
malformed, timeout, and upstream-error responses separately.

The infrastructure status endpoint includes embedding readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/infrastructure/status
```

Required local models:

- Chat model: value of `OLLAMA_MODEL`, default `qwen3:14b`
- Embedding model: value of `OLLAMA_EMBEDDING_MODEL`, default `embeddinggemma`

Application code does not pull or download Ollama models automatically.

## Environment Variables

```powershell
$env:OLLAMA_MODEL = "qwen3:14b"
$env:OLLAMA_EMBEDDING_MODEL = "embeddinggemma"
$env:OLLAMA_NUM_PREDICT = "768"
$env:OLLAMA_THINK = "false"
$env:REQUEST_TIMEOUT_SECONDS = "300"
$env:EMBEDDING_VALIDATION_TIMEOUT_SECONDS = "10"
$env:PERFORMANCE_LOG_PATH = "B:\CTV_AI\logs\performance.jsonl"
```

`OLLAMA_NUM_PREDICT` bounds generated output length. It is intentionally separate
from the HTTP timeout; increasing the timeout is not the primary performance fix.
`OLLAMA_THINK=false` asks supported Ollama reasoning models to return the final
answer directly instead of spending the prediction budget on hidden thinking.

## Supported Ollama Chat Shape

The backend accepts the installed Ollama non-streaming `/api/chat` shape:

- HTTP 2xx
- JSON object
- no top-level `error`
- `message` object
- non-empty string `message.content`
- `done` is not `false`
- `done_reason` is not `length` or `num_predict`

The backend records only sanitized response structure before rejecting invalid
responses: status, content type, top-level keys, message keys, content/thinking
lengths, `done`, `done_reason`, model, token counts, and duration fields.

## Performance Logs

Structured performance events continue to go to stdout and are also persisted as
JSON Lines at `logs/performance.jsonl` by default. The file rotates according to:

- `PERFORMANCE_LOG_MAX_BYTES`
- `PERFORMANCE_LOG_BACKUP_COUNT`

Events are sanitized and must not include prompts, answers, document text, bearer
tokens, API keys, or employee personal data.

## Qdrant Category Check

The router emits stable collection slugs, then retrieval resolves aliases to
stored Qdrant metadata categories. Current aliases include:

- `brand-guidelines` -> `branding`
- `project-references` -> `branding`
- `equipment-manuals` -> `cameras`
- `technical-documentation` -> `cameras`, `editing`
- `production-sops` -> `editing`

To inspect categories manually, use the Qdrant collection scroll API or a local
script that counts payload `category` values without printing document text.

## Single-Case Diagnostic

Use the diagnostic helper to run one benchmark prompt and print sanitized fields:

```powershell
$env:CTV_ONE_API_ROOT = "http://127.0.0.1:8000/api/v1"
$env:CTV_ONE_BEARER_TOKEN = "<paste bearer token>"
$env:CTV_ONE_BENCHMARK_CASE = "operations_priorities"
python .\scripts\company_brain_case_diagnostic.py
```

It prints request ID, HTTP status, duration, result type, safe error category,
prompt-size metrics, Ollama metadata, and structural error diagnostics when
available. It does not print prompts, answers, task contents, employee data, or
secrets.

First-token latency is deferred to P1.3. The current Company Brain ask path uses
non-streaming Ollama chat, so first-token latency cannot be measured truthfully
without adding an internal streaming measurement path.

## Run The Benchmark

From Windows PowerShell:

```powershell
$env:CTV_ONE_API_ROOT = "http://127.0.0.1:8000"
$env:CTV_ONE_BEARER_TOKEN = "<paste bearer token>"
$env:CTV_ONE_BENCHMARK_TIMEOUT_SECONDS = "420"
python .\scripts\company_brain_baseline.py
```

Optional output directory:

```powershell
$env:CTV_ONE_BENCHMARK_OUTPUT_DIR = ".\benchmarks\reports"
```

Reports are saved as JSON, CSV, and Markdown under `benchmarks/reports` by default.
The bearer token is used only for request headers and is not written to reports.

## Cold And Warm Baselines

For a cold baseline, restart the backend and Ollama, then run the benchmark once.
Do not send a manual warmup request first.

For a warm baseline, run the benchmark a second time without restarting services.
Compare request durations, `ollama_total`, Ollama `load_duration`, and calculated
tokens per second between the two report sets.

## Limitations

- No live benchmark is required by unit tests.
- Failed benchmark cases continue so later prompts still run.
- The benchmark measures endpoint behavior from the client side, while structured
  backend logs provide internal stage timings.
- No secrets, prompts, answers, document text, API keys, or employee personal details
  are included in structured performance logs.
