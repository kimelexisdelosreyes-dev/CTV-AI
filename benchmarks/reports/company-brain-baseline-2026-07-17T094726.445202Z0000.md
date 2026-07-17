# Company Brain Baseline Benchmark

- Generated at: 2026-07-17T09:47:26.445202+00:00
- API root: http://127.0.0.1:8001
- Timeout seconds: 420.0
- Successful requests: 10/10

| # | Case | Result | Context | Prompt chars | Tokens | Model | Previous | Same model | First for model | Role | Complexity | Fallback | Budget | Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | Saved est. ms | Degraded | Success | Status | Seconds | Sources | Ops tasks | Error |
| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | operations_priorities | generated_answer | operations,system | 2312 | 578 | qwen3:8b |  | None | True | operations | moderate | False | False | False | 65.604 | snapshot | 99.422 | fresh |  | False | True | 200 | 43.184 | 0 | 6 |  |
| 2 | overdue_tasks | generated_answer | operations,system | 2267 | 567 | qwen3:8b | qwen3:8b | True | False | operations | moderate | False | False | False | 100.762 | snapshot | 142.661 | fresh |  | False | True | 200 | 36.171 | 0 | 6 |  |
| 3 | company_policy | generated_answer | knowledge,system | 3667 | 917 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 8832.719 |  |  |  |  | False | True | 200 | 50.14 | 4 | 0 |  |
| 4 | equipment_manual | generated_answer | knowledge,system | 3672 | 918 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 836.513 |  |  |  |  | False | True | 200 | 46.635 | 4 | 0 |  |
| 5 | production_sop | generated_answer | knowledge,system | 3664 | 916 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 785.594 |  |  |  |  | False | True | 200 | 43.275 | 4 | 0 |  |
| 6 | technical_troubleshooting | generated_answer | knowledge,system | 3673 | 919 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 490.864 |  |  |  |  | False | True | 200 | 37.88 | 4 | 0 |  |
| 7 | brand_guidance | generated_answer | knowledge,system | 2191 | 548 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | False | False | 752.93 |  |  |  |  | False | True | 200 | 35.912 | 4 | 0 |  |
| 8 | mixed_operations_plus_knowledge | generated_answer | knowledge,operations,system | 4441 | 1111 | qwen3:8b | qwen3:8b | True | False | balanced | complex | False | False | True | 1068.567 | snapshot | 73.803 | fresh | 28.299999999999955 | False | True | 200 | 51.498 | 4 | 6 |  |
| 9 | employee_context_question | no_knowledge_fallback | employee,system | 756 | 189 | qwen3:8b | qwen3:8b | True | False | fast | simple | False | False | False | 48.617 |  |  |  |  | False | True | 200 | 15.853 | 0 | 0 |  |
| 10 | repeat_operations_priorities | generated_answer | operations,system | 2313 | 579 | qwen3:8b | qwen3:8b | True | False | operations | moderate | False | False | False | 27.15 | snapshot | 141.002 | fresh |  | False | True | 200 | 38.198 | 0 | 6 |  |
