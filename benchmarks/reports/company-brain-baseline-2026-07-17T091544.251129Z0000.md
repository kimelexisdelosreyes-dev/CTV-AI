# Company Brain Baseline Benchmark

- Generated at: 2026-07-17T09:15:44.251129+00:00
- API root: http://127.0.0.1:8001
- Timeout seconds: 420.0
- Successful requests: 10/10

| Case | Result | Context | Prompt chars | Tokens | Model | Role | Complexity | Fallback | Budget | Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | Saved est. ms | Degraded | Success | Status | Seconds | Sources | Ops tasks | Error |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| operations_priorities | generated_answer | operations,system | 2313 | 579 | qwen3:14b | operations | moderate | False | False | False | 58.37 | snapshot | 122.065 | fresh |  | False | True | 200 | 199.055 | 0 | 6 |  |
| overdue_tasks | generated_answer | operations,system | 2267 | 567 | qwen3:14b | operations | moderate | False | False | False | 22.569 | snapshot | 321.036 | stale |  | False | True | 200 | 146.452 | 0 | 6 |  |
| company_policy | generated_answer | knowledge,system | 3667 | 917 | qwen3:8b | knowledge | moderate | False | True | False | 2004.386 |  |  |  |  | False | True | 200 | 55.552 | 4 | 0 |  |
| equipment_manual | generated_answer | knowledge,system | 3672 | 918 | qwen3:8b | knowledge | moderate | False | True | False | 1981.783 |  |  |  |  | False | True | 200 | 63.814 | 4 | 0 |  |
| production_sop | generated_answer | knowledge,system | 3664 | 916 | qwen3:8b | knowledge | moderate | False | True | False | 869.428 |  |  |  |  | False | True | 200 | 50.524 | 4 | 0 |  |
| technical_troubleshooting | generated_answer | knowledge,system | 3673 | 919 | qwen3:8b | knowledge | moderate | False | True | False | 552.454 |  |  |  |  | False | True | 200 | 53.201 | 4 | 0 |  |
| brand_guidance | generated_answer | knowledge,system | 2191 | 548 | qwen3:8b | knowledge | moderate | False | False | False | 763.69 |  |  |  |  | False | True | 200 | 27.72 | 4 | 0 |  |
| mixed_operations_plus_knowledge | generated_answer | knowledge,operations,system | 4442 | 1111 | qwen3:14b | balanced | complex | False | False | True | 1015.346 | snapshot | 322.755 | stale | 30.58400000000006 | False | True | 200 | 88.431 | 4 | 6 |  |
| employee_context_question | no_knowledge_fallback | employee,system | 756 | 189 | qwen3:8b | fast | simple | False | False | False | 46.565 |  |  |  |  | False | True | 200 | 25.383 | 0 | 0 |  |
| repeat_operations_priorities | generated_answer | operations,system | 2313 | 579 | qwen3:14b | operations | moderate | False | False | False | 25.934 | snapshot | 113.564 | fresh |  | False | True | 200 | 59.558 | 0 | 6 |  |
