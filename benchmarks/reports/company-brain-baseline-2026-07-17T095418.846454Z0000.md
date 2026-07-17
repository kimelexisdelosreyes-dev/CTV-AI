# Company Brain Baseline Benchmark

- Generated at: 2026-07-17T09:54:18.846454+00:00
- API root: http://127.0.0.1:8001
- Timeout seconds: 420.0
- Successful requests: 10/10

| # | Case | Result | Context | Prompt chars | Tokens | Model | Previous | Same model | First for model | Role | Complexity | Fallback | Budget | Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | Saved est. ms | Degraded | Success | Status | Seconds | Sources | Ops tasks | Error |
| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | operations_priorities | generated_answer | operations,system | 2313 | 579 | qwen3:8b |  | None | True | operations | moderate | False | False | False | 23.069 | snapshot | 192.573 | fresh |  | False | True | 200 | 38.696 | 0 | 6 |  |
| 2 | overdue_tasks | generated_answer | operations,system | 2267 | 567 | qwen3:8b | qwen3:8b | True | False | operations | moderate | False | False | False | 26.72 | snapshot | 231.283 | fresh |  | False | True | 200 | 31.682 | 0 | 6 |  |
| 3 | company_policy | generated_answer | knowledge,system | 3667 | 917 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 747.483 |  |  |  |  | False | True | 200 | 29.807 | 4 | 0 |  |
| 4 | equipment_manual | generated_answer | knowledge,system | 3672 | 918 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 741.667 |  |  |  |  | False | True | 200 | 27.826 | 4 | 0 |  |
| 5 | production_sop | generated_answer | knowledge,system | 3664 | 916 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 730.34 |  |  |  |  | False | True | 200 | 26.087 | 4 | 0 |  |
| 6 | technical_troubleshooting | generated_answer | knowledge,system | 3673 | 919 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | True | False | 435.235 |  |  |  |  | False | True | 200 | 25.522 | 4 | 0 |  |
| 7 | brand_guidance | generated_answer | knowledge,system | 2191 | 548 | qwen3:8b | qwen3:8b | True | False | knowledge | moderate | False | False | False | 716.415 |  |  |  |  | False | True | 200 | 19.077 | 4 | 0 |  |
| 8 | mixed_operations_plus_knowledge | generated_answer | knowledge,operations,system | 4441 | 1111 | qwen3:8b | qwen3:8b | True | False | balanced | complex | False | False | True | 1004.072 | snapshot | 71.862 | fresh | 28.130999999999972 | False | True | 200 | 34.957 | 4 | 6 |  |
| 9 | employee_context_question | no_knowledge_fallback | employee,system | 756 | 189 | qwen3:8b | qwen3:8b | True | False | fast | simple | False | False | False | 5.259 |  |  |  |  | False | True | 200 | 25.144 | 0 | 0 |  |
| 10 | repeat_operations_priorities | generated_answer | operations,system | 2313 | 579 | qwen3:8b | qwen3:8b | True | False | operations | moderate | False | False | False | 27.298 | snapshot | 131.831 | fresh |  | False | True | 200 | 31.162 | 0 | 6 |  |
