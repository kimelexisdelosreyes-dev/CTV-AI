# Company Brain Baseline Benchmark

- Generated at: 2026-07-17T08:36:52.097112+00:00
- API root: http://127.0.0.1:8000/api/v1
- Timeout seconds: 420
- Successful requests: 10/10

| Case | Result | Context | Prompt chars | Tokens | Budget | Parallel | Retrieval ms | Ops source | Snapshot age | Freshness | Saved est. ms | Degraded | Success | Status | Seconds | Sources | Ops tasks | Error |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| operations_priorities | generated_answer | operations,system | 2311 | 578 | False | False | 24.136 | snapshot | 2.829 | fresh |  | False | True | 200 | 71.834 | 0 | 6 |  |
| overdue_tasks | generated_answer | operations,system | 2266 | 567 | False | False | 28.623 | snapshot | 74.666 | fresh |  | False | True | 200 | 65.672 | 0 | 6 |  |
| company_policy | generated_answer | knowledge,system | 3667 | 917 | True | False | 2509.964 |  |  |  |  | False | True | 200 | 30.831 | 4 | 0 |  |
| equipment_manual | generated_answer | knowledge,system | 3672 | 918 | True | False | 1001.701 |  |  |  |  | False | True | 200 | 46.699 | 4 | 0 |  |
| production_sop | generated_answer | knowledge,system | 3664 | 916 | True | False | 977.799 |  |  |  |  | False | True | 200 | 75.358 | 4 | 0 |  |
| technical_troubleshooting | generated_answer | knowledge,system | 3673 | 919 | True | False | 513.199 |  |  |  |  | False | True | 200 | 88.835 | 4 | 0 |  |
| brand_guidance | generated_answer | knowledge,system | 2191 | 548 | False | False | 820.095 |  |  |  |  | False | True | 200 | 37.029 | 4 | 0 |  |
| mixed_operations_plus_knowledge | generated_answer | knowledge,operations,system | 4441 | 1111 | False | True | 1125.549 | snapshot | 99.227 | fresh | 84.25199999999995 | False | True | 200 | 91.437 | 4 | 6 |  |
| employee_context_question | no_knowledge_fallback | employee,system | 756 | 189 | False | False | 53.117 |  |  |  |  | False | True | 200 | 26.758 | 0 | 0 |  |
| repeat_operations_priorities | generated_answer | operations,system | 2313 | 579 | False | False | 29.644 | snapshot | 217.256 | fresh |  | False | True | 200 | 61.634 | 0 | 6 |  |
