# CTV ONE Enterprise Intelligence v2.0 — Chapter 1

## Purpose

The Executive Supervisor adds bounded, read-only coordination to Company Brain. It decides whether the existing direct path is sufficient, builds an inspectable plan only for composite work, executes registered specialists in a validated dependency graph, and composes validated results. It is orchestration infrastructure, not an autonomous action system.

## Existing request flow and insertion point

Both Company Brain routes authenticate and validate before calling `answer_with_knowledge()`. That service performs deterministic intent and context-requirement routing, then attempts the existing semantic-cache lookup. An exact or safe semantic hit returns immediately. On a miss, the supervisor pre-classifier runs before the existing retrieval coordinator. This is the insertion point because it preserves cache speed and lets direct requests continue through the unchanged retrieval, prompt assembly, model routing, bounded inference queue, Ollama call, persistence, and instrumentation path.

The authenticated ORM user is converted to an immutable request-scoped identity containing only user ID, display name, and role before any read-transaction rollback. Retrieval, inference admission, agent permissions, employee self-context, and conversation persistence use that stable identity. This prevents SQLAlchemy from attempting implicit asynchronous reloads of expired authentication objects after transaction cleanup. Both `direct` and `fallback_direct` fall through the same existing retrieval and inference continuation; neither requires a `SupervisorResult`.

Current read sources are approved vector knowledge, the active Monday operations snapshot, authenticated employee self-context, and conversation history. Operations-only routing can avoid vector retrieval. Existing controlled service errors remain the direct path's fallback boundary.

## Modes and deterministic selection

- `direct` uses the existing Company Brain path. Single-domain knowledge, operations, and employee requests stay here. Prompt length is not a planning signal.
- `supervised` is selected for recognized composite domains or a domain combined with an explicit comparison, synthesis, recommendation, risk, or trade-off request. A caller may explicitly request it.
- `fallback_direct` returns to the existing path when planning cannot safely produce a valid bounded plan and fallback is enabled.

The request field `supervisor_mode` accepts `auto`, `direct`, or `supervised` and defaults to `auto`. Disabling the supervisor makes all requests direct.

## Agent registry

`AgentRegistry` owns concrete agent instances registered by the application. Every definition declares its stable ID, description, capabilities, supported intents, permissions, input/output schema names, cost class, parallel support, enablement, and version. Registration rejects duplicate IDs and undeclared capabilities. Resolution excludes disabled agents. Plans cannot supply import paths or construct arbitrary agents.

The initial read-only agents are:

- `knowledge_agent`: approved knowledge search, policy lookup, document summary, and evidence retrieval.
- `operations_agent`: active snapshot status, overdue work, priorities, workload, and project status.
- `employee_agent`: authenticated-user self-context, responsibilities, role, and department context.
- `reasoning_agent`: comparison, synthesis, recommendations, risk, and trade-offs over validated dependency results only.
- `response_composer_agent`: final answers, executive summaries, and structured briefs from validated results only.

## Planning and execution graph

Known domain combinations use deterministic decomposition. An LLM planner is used only when forced or composite work cannot be safely decomposed. It receives the request plus safe allowed-agent metadata, returns strict JSON, and runs through the existing inference queue with a dedicated 20-second default timeout, independent of the 60-second agent-task timeout. Every plan is then validated for registered agents, declared capabilities, caller permissions, unique tasks, known dependencies, acyclicity, task count, and dependency depth.

The execution engine schedules ready DAG nodes with asyncio, preserves dependency order, caps parallel batches, prevents duplicate task execution, and applies per-task and total-plan timeouts. It releases inference leases on success, timeout, or cancellation. Database read transactions are rolled back before parallel execution waits.

Required dependency failure skips dependents. Optional failure allows downstream work to continue. Malformed result contracts become safe failed results. Evidence is deduplicated, capped by count and total characters, and retains attribution. The composer receives only successful, validated dependency results.

## Permissions and security boundaries

Capabilities map centrally to permissions derived from the authenticated user. Validation rejects unauthorized work before execution; the supervisor cannot add permissions. Employee retrieval is restricted to the authenticated user's existing visibility scope. Existing knowledge and operations services remain the enforcement points for their data.

Agents are read-only. They cannot perform external writes, call the supervisor, create recursive plans, load arbitrary tools, or receive unrestricted internal state. Metrics, diagnostics, and stream events exclude questions, answers, employee identifiers, prompts, agent inputs, and hidden reasoning.

## Streaming lifecycle

The direct protocol remains `start`, `context_ready`, `token`, and `done`. Supervised streams may additionally emit `supervisor_mode`, `plan_ready`, `agent_started`, `agent_completed`, and `composition_started`. Existing clients may ignore unknown event names. Disconnect cancellation propagates to preparation, active tasks, and inference leases.

## Failure policy

- Planner failure records a safe category and uses `fallback_direct` when enabled.
- Required task failure skips dependent tasks; available independent results can still form a partial response.
- Optional task failure adds a safe warning and composition continues.
- Composer failure uses a deterministic summary of validated successful results.
- A task or total-plan timeout records `timed_out` without exposing underlying prompts or raw service errors.
- Unexpected direct errors retain their server-side traceback and are logged with request ID plus a safe category; clients receive only a controlled error response and correlation headers.

## Cache policy

Direct requests retain the existing semantic-cache lookup and write behavior, and cache hits bypass planning. Supervised result caching is disabled by default. A future supervised cache key is defined as a SHA-256 fingerprint over the normalized request, selected capabilities, knowledge revision, operations content hash, employee scope, agent versions, planner version, and composer prompt version. It must not be enabled until all source revisions are reliably supplied and correctness is validated.

## Observability and diagnostics

Request instrumentation records mode, planning requirement and type, task count/depth, selected agents, planning/execution/composition/total latency, parallelism peak, task outcomes and timeouts, partial/fallback/direct/cache flags, and a safe error category. It also retains existing inference-queue metrics.

Administrators can inspect aggregate state at `GET /api/v1/runtime/supervisor/status`: registry metadata, enabled/capability counts, active/completed/failed/partial plans, bypass/fallback totals, average task and latency data, safe error categories, and configured limits. The endpoint never returns request or result content.

Chapter 2 wraps these agents in a lifecycle and capability runtime. See `ENTERPRISE_INTELLIGENCE_V2_CHAPTER_2.md`; Chapter 1 direct, cache, and fallback behavior remains the compatibility baseline.

## Configuration

```dotenv
CTV_ONE_SUPERVISOR_ENABLED=true
CTV_ONE_SUPERVISOR_DEFAULT_MODE=auto
CTV_ONE_SUPERVISOR_LLM_PLANNING_ENABLED=true
CTV_ONE_SUPERVISOR_MAX_TASKS=6
CTV_ONE_SUPERVISOR_MAX_DEPTH=3
CTV_ONE_SUPERVISOR_MAX_PARALLEL_TASKS=3
CTV_ONE_SUPERVISOR_PLANNER_TIMEOUT_SECONDS=20
CTV_ONE_SUPERVISOR_TASK_TIMEOUT_SECONDS=60
CTV_ONE_SUPERVISOR_TOTAL_TIMEOUT_SECONDS=180
CTV_ONE_SUPERVISOR_FALLBACK_DIRECT=true
CTV_ONE_SUPERVISOR_CACHE_ENABLED=false
CTV_ONE_SUPERVISOR_STREAM_EVENTS_ENABLED=true
```

These defaults target one local AI core. The tracked example documents them; the local `.env` remains operator-owned.

## Benchmark procedure

With the backend running and a bearer token available, run:

```powershell
$env:CTV_ONE_API_ROOT='http://127.0.0.1:8000'
$env:CTV_ONE_BEARER_TOKEN='<token>'
backend\.venv\Scripts\python.exe scripts\company_brain_baseline.py
```

The benchmark retains the original Company Brain cases and adds ten supervisor cases covering direct knowledge, direct operations, composite domain plans, recommendation and executive composition, planner fallback behavior, optional partial behavior, the streaming route, and a repeated direct cache candidate. JSON and CSV output include supervisor mode/type/tasks/agents, stage and total latency, peak parallelism, fallback/partial status, queue wait, cache state, and success. The planner-failure case uses benchmark-local injection and sends the authenticated fallback request through direct mode, so it never waits on a real planner timeout. Runtime planner timeout and fallback dispatch are validated offline; the public API exposes no failure controls.

## Deferred capabilities

This chapter does not include autonomous external actions, persistent organizational memory, universal NAS or Drive search, creative generation workflows, workflow automation, approval execution, or recursive agents. Those capabilities require separate security, consent, evaluation, and audit work in later chapters.
