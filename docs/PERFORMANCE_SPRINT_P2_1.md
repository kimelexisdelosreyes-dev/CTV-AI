# Performance Sprint P2.1: Parallel Context Retrieval

## Request Lifecycle

Company Brain requests enter through `POST /api/v1/knowledge/ask`.

1. The API route resolves the requested knowledge collection and persists the user
   message when a conversation ID is present.
2. `answer_with_knowledge()` runs deterministic intelligence routing and derives
   `ContextRequirements`.
3. `ContextRetrievalCoordinator` fetches eligible context components.
4. Prompt assembly applies per-component and total prompt budgets in deterministic
   section order.
5. Ollama inference runs after retrieval and prompt assembly complete.
6. The API route persists the visible assistant message and returns the existing
   `KnowledgeAskResponse` shape with additive safe context metadata.

## Parallel Retrieval Architecture

The coordinator receives finalized routing and requirements, then launches only
the selected independent context sources:

- knowledge retrieval through embeddings and Qdrant
- monday.com operations retrieval
- employee context retrieval
- conversation history loading

Prompt ordering does not depend on task completion order. The prompt is always
assembled as:

1. Knowledge Context
2. Operational Context
3. Employee Context
4. Conversation History

## Concurrency Eligibility Matrix

| Component | Runs in parallel with | Notes |
| --- | --- | --- |
| Knowledge | Operations, DB context task | Depends on router-selected collections. |
| Operations | Knowledge, DB context task | Uses connector reads, not the request DB session. |
| Employee | Knowledge, Operations | Uses the request `AsyncSession`. |
| History | Knowledge, Operations | Uses the request `AsyncSession`. |
| Employee + History | Not parallel with each other | Kept sequential to avoid concurrent `AsyncSession` use. |

## Database Session Safety

The request-scoped SQLAlchemy `AsyncSession` is not shared across concurrent DB
operations. When employee context and conversation history are both required,
the coordinator runs them sequentially inside one database-context task. That
database task may still run concurrently with knowledge and operations retrieval.

## Mandatory And Optional Context

- Knowledge is mandatory when `include_knowledge` is true.
- Operations is mandatory when `include_operations` is true.
- Employee context is mandatory for the employee route and optional for
  personalization elsewhere.
- Conversation history is optional.

Required component failure raises a controlled `CompanyBrainServiceError`.
Optional component failure degrades the answer and records safe metadata:
`context_degraded`, `unavailable_context_components`, and
`required_context_failure`.

## Timeout Behavior

Retrieval uses component-level timeouts:

- `COMPANY_BRAIN_KNOWLEDGE_TIMEOUT_SECONDS`
- `COMPANY_BRAIN_OPERATIONS_TIMEOUT_SECONDS`
- `COMPANY_BRAIN_EMPLOYEE_TIMEOUT_SECONDS`
- `COMPANY_BRAIN_HISTORY_TIMEOUT_SECONDS`

Timed-out required components fail with a `context_<component>_timeout`
category. Timed-out optional components degrade safely. The overall request
timeout remains authoritative.

## Performance Metrics

Safe instrumentation records:

- `retrieval_parallel_used`
- `retrieval_total_duration_ms`
- `<component>_retrieval_duration_ms`
- `required_context_components`
- `successful_context_components`
- `failed_context_components`
- `timed_out_context_components`
- `context_degraded`
- `sequential_estimated_duration_ms`
- `parallel_time_saved_estimate_ms`
- `prompt_assembly_duration_ms`
- `inference_start_offset_ms`

No prompts, answers, retrieved chunks, monday task details, employee records,
credentials, or tokens are logged.

## Benchmark Comparison

The baseline benchmark and single-case diagnostic read safe metrics from the
structured performance log. Compare retrieval wall time against
`sequential_estimated_duration_ms`; treat `parallel_time_saved_estimate_ms` as an
estimate, not a measured sequential control run.

## Deferred Optimizations

Deferred to later phases:

- response streaming
- first-token latency work
- semantic cache
- broad response cache
- dynamic model routing
- GPU queue management
- background monday synchronization
- server-side operations snapshots
- admin performance dashboard
