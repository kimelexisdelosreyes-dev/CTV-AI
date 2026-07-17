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
