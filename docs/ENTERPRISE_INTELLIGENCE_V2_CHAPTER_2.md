# CTV ONE Enterprise Intelligence v2.0 — Chapter 2

## Purpose and scope

Chapter 2 adds a production-oriented lifecycle and capability boundary around the five read-only Chapter 1 agents. It standardizes registration, initialization, health, readiness, capability resolution, execution budgets, dependencies, enablement, compatibility, safe plugins, diagnostics, metrics, and conformance testing. Direct Company Brain execution is unchanged: semantic-cache hits and direct requests do not enter runtime planning or capability resolution.

This chapter does not add Hokkien AI, external side effects, autonomous workflow execution, persistent enterprise memory, NAS or Google Drive indexing, creative-generation agents, remote plugin installation, or distributed agent workers.

## Existing architecture analysis

Before Chapter 2, `app/supervisor/agents.py` instantiated all five agents and `build_agent_registry()` registered them directly. `AgentRegistry` checked duplicate IDs, non-empty capability sets, and capability-name syntax. The deterministic planner hard-coded agent IDs for knowledge, operations, employee, reasoning, and composition; the LLM planner received enabled registry metadata. Plan validation checked agent/capability declarations, permissions, output contracts, graph validity, task count/depth, and configured task timeouts.

The execution engine began an agent call after DAG dependencies completed, applied per-task and total-plan timeouts, validated typed results and known output shapes, bounded evidence, emitted safe events, and isolated failures. Reasoning and composition used the inference queue before Ollama and always released the lease. Retrieval agents used their existing Company Brain, operations-snapshot, and employee-context services. Safe process-local supervisor counters backed the administrator status endpoint.

The missing governance points were lifecycle state, startup initialization, health/readiness, dependency declarations, version compatibility, deterministic resolution among multiple implementers, department/role enablement, resource budgets, a standard error taxonomy, safe internal plugins, and a reusable conformance harness. Adding a future domain also required editing the supervisor's construction and hard-coded planner mapping.

Chapter 2 inserts lifecycle hooks at application lifespan startup/shutdown and capability resolution between plan construction and plan validation, with a second resolution at task dispatch to catch health changes. No request initializes an agent. Future agents are registered through an approved plugin and become discoverable by capability; supervisor internals do not need a new construction branch.

## Runtime manager architecture

`AgentRuntimeManager` owns immutable definitions, runtime records, lifecycle transitions, dependency validation, bounded hooks, health polling, enablement, active-execution counts, capability resolution, shutdown, and diagnostics. The application lifespan starts the inference queue, initializes the runtime from an application-owned dependency map, and later drains and shuts down agents before stopping the inference queue.

An optional-agent initialization failure is logged server-side with a safe category and does not crash startup. A required-agent initialization failure fails startup. Disabled agents skip initialization. Health polling is bounded, configurable, and disabled by the test process configuration.

## Lifecycle model

States are `registered`, `initializing`, `ready`, `degraded`, `unavailable`, `disabled`, `draining`, `stopped`, and `failed`. The manager validates every transition and records registration, initialization, state-change, drain, stop, and health timestamps. Ready and degraded agents may accept work. Disabled, unavailable, draining, stopped, failed, and uninitialized agents cannot.

Built-in agents implement lightweight `initialize`, `health_check`, `readiness_check`, `drain`, and idempotent `shutdown` hooks. Health checks never invoke generation, refresh Monday snapshots, or perform knowledge retrieval. Repeated failures degrade and then make an agent unavailable; the configured number of successful checks restores readiness.

## Agent definitions and version compatibility

Definitions are frozen Pydantic models containing stable ID, display name, semantic version, runtime contract version, capabilities, intents, permissions, dependencies, required/optional status, default enablement, parallel/streaming support, cost class, timeouts, default budget, department/role allowlists, schema versions, tags, and deterministic priority.

The runtime and supervisor plan contract versions are `1.0`. Major mismatches are rejected. A candidate minor version must not exceed the runtime minor version. Execution-plan tasks record agent, capability, and contract versions. Definitions accept legacy Chapter 1 constructor aliases (`name`, `input_schema`, `output_schema`, and `enabled`) while storing the Chapter 2 fields.

## Capability catalog and deterministic resolution

The central catalog contains the Chapter 1 knowledge, operations, employee, reasoning, and composition capabilities. Every catalog entry declares schemas, required permissions, classification, read-only/side-effect flags, streaming support, timeout, result-size limit, evidence requirement, compatible contracts, deprecation metadata, and partial-result policy.

Unknown and duplicate capabilities fail registration. Chapter 2 rejects write or external-side-effect capabilities. Agent permissions must meet or exceed catalog permissions. Resolution is deterministic and does not use an LLM. It considers runtime state, global and agent enablement, capability disablement, caller permissions, department/role allowlists, contract/schema compatibility, preferred agent, degradation, configured priority, and stable agent ID. The result records all candidates, safe exclusions, selected agent, reason, fallback availability, contract version, and latency.

Optional unresolved tasks are removed before final plan validation and downstream dependencies are repaired. An unresolved required capability causes the existing supervised fallback-direct behavior or a safe failure, according to configuration. A dispatch-time re-resolution can select a ready fallback if the planned agent becomes unavailable.

## Health, readiness, and dependencies

`AgentHealth` records a safe status/message, timing, safe dependency categories, consecutive failures, and success/failure timestamps. `AgentReadiness` records readiness, a safe reason category, and per-capability availability. Diagnostics never include service credentials, URLs containing credentials, stack traces, prompts, inputs, or outputs.

Dependencies use a closed enum: knowledge service, operations snapshot service, employee intelligence service, inference queue, Ollama client, semantic cache, and database adapter. The built-in plugin receives only an application-defined map. No request strings, environment import paths, or arbitrary service lookups can populate it. Request execution receives an immutable user snapshot and an explicit narrow `AgentRuntimeServices` object; it never receives a live authentication ORM object.

## Execution budgets

Every task receives a server-bounded `AgentExecutionBudget`: timeout, inference calls, retrieval calls, evidence items, input/output characters, estimated prompt tokens, queue wait, cost class, and partial-result permission. The effective budget is the minimum of plan request, agent default/maximum, and system maximum. Request input cannot raise server maxima.

The current retrieval agents report one retrieval and zero inference calls. Reasoning and composition report one inference call and zero retrieval calls. Output and evidence are validated after execution; timeouts stop work through structured cancellation. There are no loops or unlimited model-call paths. Budget violations return `agent_budget_exceeded`, emit a safe optional `budget_warning`, and retain no raw payload.

## Enablement policy

The runtime supports global enablement, per-core-agent booleans, immutable definition defaults, department/role allowlists, and a comma-separated server-owned capability disable list. Enablement is evaluated before planning and again at dispatch. Forced supervision cannot bypass it. Disabling an optional agent does not affect direct mode. The required composer falls back to the existing deterministic summary/direct behavior when it cannot be resolved. Ordinary users cannot mutate runtime policy.

## Safe plugin registration

The built-in `ctv_one_core_agents` plugin explicitly registers the five approved agents. `PluginRegistry` has a code-owned plugin allowlist, semantic versions, runtime-contract checks, duplicate rejection, safe failure isolation, and diagnostics. There is no filesystem scan, package entry-point loading, dynamic import path, remote code, installation, or self-registration from a request.

## Supervisor and streaming integration

The semantic-cache fast path remains before supervisor selection. Direct and fallback-direct behavior retain the Chapter 1 continuation and incur no runtime planning overhead. Supervised plans are capability-resolved, version-stamped, validated, and dispatched through the runtime. Agents cannot call the supervisor, execute recursively, access undeclared capabilities, or obtain unrestricted application state.

Existing stream events remain compatible. Supervised streams may additionally emit:

- `agent_resolved`: task ID, capability, stable agent ID, and agent version.
- `agent_degraded`: task ID, stable agent ID, and safe reason category.
- `budget_warning`: task ID, stable agent ID, and bounded budget category.

No event exposes prompts, hidden reasoning, task content, credentials, private employee identifiers, or internal dependency details.

## Error taxonomy

The runtime maps failures deterministically to: `agent_disabled`, `agent_unavailable`, `agent_not_ready`, `agent_initialization_failed`, `agent_health_failed`, `agent_dependency_unavailable`, `agent_permission_denied`, `agent_capability_unsupported`, `agent_contract_mismatch`, `agent_budget_exceeded`, `agent_queue_timeout`, `agent_execution_timeout`, `agent_cancelled`, `agent_result_invalid`, `agent_dependency_failed`, and `agent_internal_error`.

Unexpected failures are logged with server-side traceback and only `agent_internal_error` is returned. Chapter 1's legacy engine-only categories remain for compatibility when the engine is deliberately constructed without a runtime manager in existing isolated tests.

## Diagnostics and metrics

Administrators may call `GET /api/v1/runtime/agents/status`. It returns runtime/version state, lifecycle counts, capability counts, polling state, approved plugins, safe per-agent definition/lifecycle/readiness/health/dependency categories, and configuration limits. Supervisor status also reports runtime readiness, resolvable-capability count, unavailable required agents, and capability-resolution failures.

Process-local bounded metrics cover initialization, lifecycle, health, readiness, executions, successes/failures/timeouts/cancellation, budgets, result validation, durations, queue/inference/retrieval/evidence usage, resolution/fallback, and plugin failures. Labels are stable registered agent/capability IDs only; user IDs, request text, plan/task IDs, employee names, and document titles are prohibited.

## Conformance harness

`backend/tests/agents/conformance.py` provides common checks for definition and contract validity, initialization, bounded health, readiness, safe messages, and idempotent shutdown. All five current agents run through it. Focused runtime tests cover immutable definitions, semantic versions, catalog constraints, lifecycle transitions, required/optional failures, disabled initialization, health degradation/recovery, deterministic fallback, permission governance, budgets, plugin isolation, diagnostics, and the offline benchmark.

## Configuration

Tracked settings are documented in `backend/.env.example`. Defaults target one local AI core:

```text
CTV_ONE_AGENT_RUNTIME_ENABLED=true
CTV_ONE_AGENT_HEALTH_POLL_ENABLED=true
CTV_ONE_AGENT_HEALTH_POLL_SECONDS=60
CTV_ONE_AGENT_HEALTH_TIMEOUT_SECONDS=5
CTV_ONE_AGENT_INITIALIZE_TIMEOUT_SECONDS=30
CTV_ONE_AGENT_SHUTDOWN_TIMEOUT_SECONDS=15
CTV_ONE_AGENT_FAILURE_THRESHOLD=3
CTV_ONE_AGENT_RECOVERY_SUCCESS_THRESHOLD=2
CTV_ONE_AGENT_KNOWLEDGE_ENABLED=true
CTV_ONE_AGENT_OPERATIONS_ENABLED=true
CTV_ONE_AGENT_EMPLOYEE_ENABLED=true
CTV_ONE_AGENT_REASONING_ENABLED=true
CTV_ONE_AGENT_COMPOSER_ENABLED=true
CTV_ONE_AGENT_DISABLED_CAPABILITIES=
CTV_ONE_AGENT_DEFAULT_MAX_INFERENCE_CALLS=1
CTV_ONE_AGENT_DEFAULT_MAX_RETRIEVAL_CALLS=3
CTV_ONE_AGENT_DEFAULT_MAX_EVIDENCE_ITEMS=12
CTV_ONE_AGENT_DEFAULT_MAX_OUTPUT_CHARS=16000
CTV_ONE_AGENT_DEFAULT_MAX_QUEUE_WAIT_SECONDS=120
```

The live `backend/.env` is user-owned and is not modified by this milestone.

## Benchmark procedure

Run the external authenticated Company Brain benchmark as documented in Chapter 1. Run the failure-injection-free offline runtime cases with:

```powershell
.\backend\.venv\Scripts\python.exe scripts\agent_runtime_benchmark.py
```

The runtime report contains ten cases: all-ready startup, direct-cache bypass, deterministic resolution, optional disabled/degraded, required unavailable, fallback selection, budget enforcement, cancellation cleanup, and streaming resolution events. Each row records selected agent/version/capability, lifecycle, resolution latency/fallback, initialization/health/budget state, queue wait, execution latency, partial/fallback flags, and success. All fault states are process-local fixtures; there is no public runtime failure switch.

## How to add a new agent

1. Define or select a catalog capability and its input/output schemas.
2. Implement the agent contract and lifecycle hooks.
3. Declare permissions, dependencies, budgets, allowlists, versions, and safe metadata.
4. Register the instance in an explicitly approved internal plugin.
5. Pass the shared conformance harness.
6. Add capability-resolution and supervisor integration tests.
7. Validate administrator diagnostics for safe metadata only.
8. Add offline and authenticated benchmark coverage.
9. Enable the agent through tracked server configuration.
10. Run the full release and security validation.

No supervisor construction branch is required when an existing planner capability maps to the new agent. A genuinely new request domain may add deterministic intent-to-capability mapping, but registration, lifecycle, resolution, dispatch, diagnostics, and failure isolation stay unchanged.

## Security boundaries and remaining limitations

The runtime is process-local and single-node. Health state and counters reset on restart. Plans are not persisted or replayed. Plugins are application code deployed with CTV ONE, not user-installed extensions. Schema validation uses the current bounded output-contract registry rather than a general schema registry. Queue-wait usage is reported when available from inference instrumentation; retrieval services retain their own deeper resource metrics. Department is not yet present in the immutable authentication snapshot, so department allowlists require an explicit trusted department value from a future identity adapter.

C2.1 adds role-specific timeout semantics, bounded composition strategies, and a hot exact-cache layer. See `ENTERPRISE_INTELLIGENCE_V2_CHAPTER_2_1.md` for timing behavior and release-validation evidence.
