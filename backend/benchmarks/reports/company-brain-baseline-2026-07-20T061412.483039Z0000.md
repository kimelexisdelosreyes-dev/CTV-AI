# Company Brain Baseline Benchmark

- Generated at: 2026-07-20T06:14:12.483039+00:00
- API root: http://127.0.0.1:8000
- Timeout seconds: 420
- Successful requests: 15/20

| # | Pass | Case | Result | Cache | Hit type | Lookup ms | Ollama skipped | Context | Prompt chars | Tokens | Model | Previous | Same model | First for model | Role | Complexity | Fallback | Budget | Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | Saved est. ms | Degraded | Success | Status | Seconds | Sources | Ops tasks | Error |
| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | cold_cache | operations_priorities | service_failure | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | False | 500 | 2.641 | 0 | None | HTTP 500 |
| 2 | cold_cache | overdue_tasks | service_failure | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | False | 500 | 0.522 | 0 | None | HTTP 500 |
| 3 | cold_cache | company_policy | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.026 | 4 | 0 |  |
| 4 | cold_cache | equipment_manual | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.059 | 4 | 0 |  |
| 5 | cold_cache | production_sop | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.018 | 4 | 0 |  |
| 6 | cold_cache | technical_troubleshooting | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.02 | 4 | 0 |  |
| 7 | cold_cache | brand_guidance | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.018 | 4 | 0 |  |
| 8 | cold_cache | mixed_operations_plus_knowledge | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 1.214 | 5 | 0 |  |
| 9 | cold_cache | employee_context_question | service_failure | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | False | 500 | 0.064 | 0 | None | HTTP 500 |
| 10 | cold_cache | repeat_operations_priorities | service_failure | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | False | 500 | 0.36 | 0 | None | HTTP 500 |
| 11 | cold_cache | supervisor_direct_knowledge | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.311 | 4 | 0 |  |
| 12 | cold_cache | supervisor_direct_operations | service_failure | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | False | 500 | 0.37 | 0 | None | HTTP 500 |
| 13 | cold_cache | supervisor_operations_plus_knowledge | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 1.152 | 5 | 0 |  |
| 14 | cold_cache | supervisor_employee_plus_operations | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.348 | 0 | 0 |  |
| 15 | cold_cache | supervisor_operations_plus_recommendation | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.111 | 0 | 0 |  |
| 16 | cold_cache | supervisor_three_agent_executive_summary | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.886 | 5 | 0 |  |
| 17 | cold_cache | supervisor_planner_fallback | no_knowledge_fallback | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 60.023 | 0 | 0 |  |
| 18 | cold_cache | supervisor_optional_partial_failure | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 3.757 | 5 | 0 |  |
| 19 | cold_cache | supervisor_streaming | generated_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 1.217 | 0 | None |  |
| 20 | cold_cache | supervisor_direct_cache_hit_under_load | cached_answer | None |  |  | None |  |  |  |  |  | None | None |  |  | False | False | None |  |  |  |  |  | None | True | 200 | 0.359 | 4 | 0 |  |
