# Company Brain Baseline Benchmark

- Generated at: 2026-07-17T06:54:11.761747+00:00
- API root: http://127.0.0.1:8000/api/v1
- Timeout seconds: 420
- Successful requests: 10/10

| Case | Result | Context | Prompt chars | Tokens | Budget | Parallel | Retrieval ms | Saved est. ms | Degraded | Success | Status | Seconds | Sources | Ops tasks | Error |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| operations_priorities | generated_answer | operations,system | 2209 | 553 | False | False | 22071.51 |  | False | True | 200 | 83.144 | 0 | 6 |  |
| overdue_tasks | generated_answer | operations,system | 2206 | 552 | False | False | 22220.729 |  | False | True | 200 | 112.337 | 0 | 6 |  |
| company_policy | generated_answer | knowledge,system | 3667 | 917 | True | False | 820.521 |  | False | True | 200 | 15.07 | 4 | 0 |  |
| equipment_manual | generated_answer | knowledge,system | 3672 | 918 | True | False | 852.164 |  | False | True | 200 | 52.238 | 4 | 0 |  |
| production_sop | generated_answer | knowledge,system | 3664 | 916 | True | False | 869.942 |  | False | True | 200 | 56.757 | 4 | 0 |  |
| technical_troubleshooting | generated_answer | knowledge,system | 3673 | 919 | True | False | 547.237 |  | False | True | 200 | 65.682 | 4 | 0 |  |
| brand_guidance | generated_answer | knowledge,system | 2191 | 548 | False | False | 822.584 |  | False | True | 200 | 25.583 | 4 | 0 |  |
| mixed_operations_plus_knowledge | generated_answer | knowledge,operations,system | 4371 | 1093 | False | True | 23318.678 | 1174.9320000000007 | False | True | 200 | 93.617 | 4 | 6 |  |
| employee_context_question | no_knowledge_fallback | employee,system | 756 | 189 | False | False | 41.501 |  | False | True | 200 | 26.84 | 0 | 0 |  |
| repeat_operations_priorities | generated_answer | operations,system | 2209 | 553 | False | False | 24752.8 |  | False | True | 200 | 77.083 | 0 | 6 |  |
