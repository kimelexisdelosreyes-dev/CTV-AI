from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.capabilities import CapabilityCatalog
from app.agents.errors import AgentErrorCategory, AgentRuntimeError
from app.agents.models import (
    AgentExecutionBudget,
    AgentHealth,
    AgentReadiness,
    DependencyIdentifier,
)
from app.agents.plugins import AgentPlugin
from app.core.config import settings
from app.services.context_engine import context_engine
from app.services.inference_queue import InferenceQueueError, inference_queue
from app.services.ollama_service import (
    OllamaInferenceTimeoutError,
    OllamaServiceError,
    ollama_service,
)
from app.services.operations_context_service import operations_context_service
from app.supervisor.agent_registry import AgentRegistry
from app.supervisor.schemas import (
    AgentDefinition,
    AgentResult,
    AgentTask,
    EvidenceItem,
)


@dataclass
class AgentExecutionContext:
    """Chapter 1 constructor retained for direct agent unit compatibility."""

    user: Any
    db: Any
    question: str
    top_k: int
    route: Any
    requirements: Any
    instrumentation: Any
    knowledge_fetcher: Any


class LifecycleAgent:
    """Safe default lifecycle hooks for stateless built-in agents."""

    _initialized = False

    async def initialize(self, runtime_context) -> None:
        self._initialized = True

    async def health_check(self) -> AgentHealth:
        return AgentHealth(status="healthy", safe_message="Built-in agent is available.")

    async def readiness_check(self) -> AgentReadiness:
        return AgentReadiness(
            ready=self._initialized,
            reason_category=None if self._initialized else "agent_not_initialized",
            capability_availability={
                capability: self._initialized for capability in self.definition.capabilities
            },
        )

    async def drain(self) -> None:
        return None

    async def shutdown(self) -> None:
        self._initialized = False


def _result(
    task: AgentTask,
    started: float,
    *,
    output: dict[str, Any],
    evidence: list[EvidenceItem] | None = None,
    warnings: list[str] | None = None,
    composition_strategy: str | None = None,
) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        agent_id=task.agent_id,
        status="success",
        structured_output=output,
        evidence=evidence or [],
        warnings=warnings or [],
        duration_ms=round((perf_counter() - started) * 1000, 3),
        composition_strategy=composition_strategy,
    )


async def invoke_agent_model(
    *,
    messages: list[dict[str, str]],
    model_name: str,
    model_role: str,
    context: AgentExecutionContext,
    agent_id: str = "reasoning_agent",
    inference_timeout_seconds: float | None = None,
) -> str:
    instrumentation = context.instrumentation
    metric_prefix = "agent_composer" if agent_id == "response_composer_agent" else "agent_reasoning"
    prompt_chars = sum(len(str(message.get("content") or "")) for message in messages)
    previous_model = getattr(instrumentation, "model_name", None) if instrumentation else None
    _record_metric(instrumentation, f"{metric_prefix}_task_model", model_name)
    _record_metric(instrumentation, f"{metric_prefix}_prompt_chars", prompt_chars)
    _record_metric(
        instrumentation,
        f"{metric_prefix}_estimated_prompt_tokens",
        (prompt_chars + 3) // 4,
    )
    _record_metric(
        instrumentation,
        f"{metric_prefix}_model_switched",
        bool(previous_model and previous_model != model_name),
    )
    if instrumentation:
        instrumentation.model_name = model_name
        instrumentation.record_metric("model_selected", model_name)
    queue_started = perf_counter()
    _record_metric(instrumentation, f"{metric_prefix}_queue_admission_started", True)
    budget = getattr(context, "budget", None)
    queue_timeout = (
        budget.max_queue_wait_seconds
        if budget is not None
        else settings.ctv_one_agent_default_max_queue_wait_seconds
    )
    try:
        admission = await inference_queue.submit(
            request_id=getattr(instrumentation, "request_id", None),
            user_id=str(context.user.id),
            model_name=model_name,
            model_role=model_role,
            streaming=False,
            estimated_cost_class=model_role,
            timeout_seconds=queue_timeout,
        )
        inference_queue.record_result(instrumentation, admission.initial_result)
        lease = await admission.wait()
    except InferenceQueueError as exc:
        _record_metric(
            instrumentation,
            f"{metric_prefix}_queue_wait_ms",
            round((perf_counter() - queue_started) * 1000, 3),
        )
        category = (
            AgentErrorCategory.QUEUE_TIMEOUT
            if exc.category == "queue_wait_timeout"
            else AgentErrorCategory.DEPENDENCY_UNAVAILABLE
        )
        raise AgentRuntimeError(category) from exc
    inference_queue.record_lease(instrumentation, lease)
    lease_result = getattr(lease, "result", None)
    queue_wait_ms = getattr(
        lease_result,
        "wait_duration_ms",
        round((perf_counter() - queue_started) * 1000, 3),
    )
    _record_metric(instrumentation, f"{metric_prefix}_queue_wait_ms", queue_wait_ms)
    _record_metric(instrumentation, f"{metric_prefix}_lease_acquired", True)
    cancelled = False
    ollama_started = perf_counter()
    _record_metric(instrumentation, f"{metric_prefix}_ollama_request_started", True)
    try:
        remaining = _remaining_deadline_seconds(getattr(context, "deadline", None))
        timeout_seconds = min(
            inference_timeout_seconds or settings.ctv_one_supervisor_task_timeout_seconds,
            remaining,
        )
        try:
            async with asyncio.timeout(max(timeout_seconds - 1.0, 0.001)):
                response = await ollama_service.chat(
                    messages,
                    model=model_name,
                    return_metadata=True,
                )
        except TimeoutError as exc:
            _record_metric(
                instrumentation,
                f"{metric_prefix}_timeout_origin",
                "inference_execution",
            )
            raise AgentRuntimeError(AgentErrorCategory.EXECUTION_TIMEOUT) from exc
        except OllamaInferenceTimeoutError as exc:
            _record_metric(
                instrumentation,
                f"{metric_prefix}_timeout_origin",
                "ollama_client",
            )
            raise AgentRuntimeError(AgentErrorCategory.EXECUTION_TIMEOUT) from exc
        except OllamaServiceError as exc:
            _record_metric(
                instrumentation,
                f"{metric_prefix}_dependency_error_category",
                exc.category,
            )
            raise AgentRuntimeError(AgentErrorCategory.DEPENDENCY_FAILED) from exc
        if isinstance(response, tuple):
            answer, metadata = response
            _record_ollama_timing(instrumentation, metric_prefix, metadata)
        else:
            answer = response
        _record_metric(
            instrumentation,
            f"{metric_prefix}_ollama_total_ms",
            round((perf_counter() - ollama_started) * 1000, 3),
        )
        return answer
    except asyncio.CancelledError:
        cancelled = True
        _record_metric(instrumentation, f"{metric_prefix}_cancelled", True)
        _record_metric(
            instrumentation,
            f"{metric_prefix}_cancellation_ms",
            round((perf_counter() - ollama_started) * 1000, 3),
        )
        raise
    finally:
        release_started = perf_counter()
        await lease.release(cancelled=cancelled)
        _record_metric(
            instrumentation,
            f"{metric_prefix}_lease_release_ms",
            round((perf_counter() - release_started) * 1000, 3),
        )
        _record_metric(instrumentation, f"{metric_prefix}_lease_released", True)


def _record_metric(instrumentation, name: str, value: object) -> None:
    if instrumentation:
        instrumentation.record_metric(name, value)


def _remaining_deadline_seconds(deadline: datetime | None) -> float:
    if deadline is None:
        return settings.ctv_one_supervisor_total_timeout_seconds
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return max((deadline - datetime.now(timezone.utc)).total_seconds(), 0.001)


def _record_ollama_timing(instrumentation, prefix: str, metadata: dict[str, object]) -> None:
    for source, target in (
        ("total_duration", "ollama_reported_total_ms"),
        ("load_duration", "model_load_ms"),
        ("prompt_eval_duration", "prompt_evaluation_ms"),
        ("eval_duration", "token_generation_ms"),
    ):
        value = metadata.get(source)
        if isinstance(value, int | float):
            _record_metric(instrumentation, f"{prefix}_{target}", round(value / 1_000_000, 3))
    for source in ("prompt_eval_count", "eval_count"):
        value = metadata.get(source)
        if isinstance(value, int | float):
            _record_metric(instrumentation, f"{prefix}_{source}", value)


class KnowledgeAgent(LifecycleAgent):
    definition = AgentDefinition(
        agent_id="knowledge_agent",
        name="Knowledge Agent",
        description="Retrieves approved Company Brain evidence.",
        capabilities=frozenset(
            {"knowledge_search", "policy_lookup", "document_summary", "evidence_retrieval"}
        ),
        supported_intents=frozenset(
            {"policy", "equipment", "production", "technical", "branding", "training", "mixed"}
        ),
        required_permissions=frozenset({"knowledge.read"}),
        input_schema="KnowledgeAgentInputV1",
        output_schema="KnowledgeEvidenceV1",
        estimated_cost_class="light",
        version="2.0.0",
        required_dependencies=frozenset({DependencyIdentifier.KNOWLEDGE_SERVICE}),
        default_budget=AgentExecutionBudget(max_inference_calls=0, max_retrieval_calls=1),
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        sources = await context.knowledge_fetcher(
            context.question,
            context.top_k,
            list(context.requirements.knowledge_collections),
            context.instrumentation,
        )
        evidence = [
            EvidenceItem(
                evidence_id=f"knowledge:{source.document_id}:{source.chunk_index}",
                citation=f"[Source {index}]",
                source_type="knowledge",
                content=source.text[:2000],
                metadata={
                    "document_id": source.document_id,
                    "filename": source.filename,
                    "category": source.category,
                    "chunk_index": source.chunk_index,
                    "page_number": source.page_number,
                    "score": source.score,
                },
            )
            for index, source in enumerate(sources[: context.top_k], start=1)
        ]
        return _result(
            task,
            started,
            output={"source_count": len(evidence), "facts": [item.content for item in evidence]},
            evidence=evidence,
            warnings=[] if evidence else ["No approved knowledge evidence was found."],
        )


class OperationsAgent(LifecycleAgent):
    definition = AgentDefinition(
        agent_id="operations_agent",
        name="Operations Agent",
        description="Reads the active Monday operations snapshot.",
        capabilities=frozenset(
            {
                "operations_status",
                "overdue_tasks",
                "priorities",
                "workload_summary",
                "project_status",
            }
        ),
        supported_intents=frozenset({"operations", "employee", "mixed"}),
        required_permissions=frozenset({"operations.read"}),
        input_schema="OperationsAgentInputV1",
        output_schema="OperationsSnapshotEvidenceV1",
        estimated_cost_class="light",
        version="2.0.0",
        required_dependencies=frozenset({DependencyIdentifier.OPERATIONS_SNAPSHOT_SERVICE}),
        default_budget=AgentExecutionBudget(max_inference_calls=0, max_retrieval_calls=1),
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        operations = await operations_context_service.build(
            context.question,
            force=True,
            instrumentation=context.instrumentation,
        )
        evidence = []
        if operations.applied and operations.text:
            evidence.append(
                EvidenceItem(
                    evidence_id="operations:active-snapshot",
                    citation="[Monday Operations]",
                    source_type="operations",
                    content=operations.text[:2000],
                    metadata={
                        "task_count": operations.task_count,
                        "board_count": operations.board_count,
                    },
                )
            )
        return _result(
            task,
            started,
            output={
                "summary": operations.summary,
                "task_count": operations.task_count,
                "board_count": operations.board_count,
                "snapshot_context": operations.text[:4000],
            },
            evidence=evidence,
            warnings=[] if operations.applied else ["Operations snapshot was unavailable."],
        )


class EmployeeAgent(LifecycleAgent):
    definition = AgentDefinition(
        agent_id="employee_agent",
        name="Employee Agent",
        description="Builds permission-scoped context for the authenticated employee.",
        capabilities=frozenset(
            {"employee_context", "responsibility_lookup", "role_context", "department_context"}
        ),
        supported_intents=frozenset({"employee", "mixed"}),
        required_permissions=frozenset({"employee.self"}),
        input_schema="EmployeeSelfContextInputV1",
        output_schema="EmployeeSelfContextV1",
        estimated_cost_class="light",
        version="2.0.0",
        required_dependencies=frozenset(
            {DependencyIdentifier.EMPLOYEE_INTELLIGENCE_SERVICE, DependencyIdentifier.DATABASE_ADAPTER}
        ),
        default_budget=AgentExecutionBudget(max_inference_calls=0, max_retrieval_calls=1),
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        bundle = await context_engine.build_employee_context(
            context.db,
            context.user,
            question=context.question,
            route=context.route,
            instrumentation=context.instrumentation,
            include_operations=False,
            max_employee_context_chars=settings.company_brain_max_employee_chars,
        )
        if isinstance(context.db, AsyncSession) and context.db.in_transaction():
            await context.db.rollback()
        evidence = [
            EvidenceItem(
                evidence_id="employee:self",
                citation="[Employee Context]",
                source_type="employee",
                content=bundle.system_context[:2000],
                metadata={"scope": "authenticated_user_only"},
            )
        ]
        return _result(
            task,
            started,
            output={"scope": "self", "employee_context": bundle.system_context[:3000]},
            evidence=evidence,
        )


def _dependency_payload(task: AgentTask) -> list[dict[str, Any]]:
    values = task.inputs.get("dependency_results", [])
    return values if isinstance(values, list) else []


NATURAL_SYNTHESIS_TERMS = {
    "compare",
    "recommend",
    "recommendation",
    "executive",
    "narrative",
    "analyze",
    "analysis",
    "risk",
    "tradeoff",
    "why",
}
COMPOSITION_AGENT_ORDER = {
    "knowledge_agent": 0,
    "operations_agent": 1,
    "employee_agent": 2,
    "reasoning_agent": 3,
}


def bounded_composition_context(
    question: str,
    results: list[dict[str, Any]],
    dependency_failures: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    ordered = sorted(
        results,
        key=lambda item: COMPOSITION_AGENT_ORDER.get(str(item.get("agent_id")), 99),
    )
    findings: list[dict[str, str]] = []
    recommendations: list[dict[str, str]] = []
    evidence: list[dict[str, str]] = []
    warnings: list[str] = []
    seen_evidence: set[str] = set()
    per_result = max(settings.ctv_one_agent_composition_max_chars_per_result, 200)
    for item in ordered:
        agent_id = str(item.get("agent_id") or "agent")
        output = item.get("structured_output")
        output = output if isinstance(output, dict) else {}
        content = _concise_result_content(agent_id, output, per_result)
        target = recommendations if agent_id == "reasoning_agent" else findings
        if content:
            target.append({"agent_id": agent_id, "content": content})
        for source in item.get("evidence", []):
            if not isinstance(source, dict) or len(evidence) >= settings.ctv_one_agent_composition_max_evidence_items:
                continue
            evidence_id = str(source.get("evidence_id") or "")
            if not evidence_id or evidence_id in seen_evidence:
                continue
            seen_evidence.add(evidence_id)
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "citation": str(source.get("citation") or ""),
                    "source_type": str(source.get("source_type") or ""),
                    "content": str(source.get("content") or "")[:900],
                }
            )
        warnings.extend(
            str(warning)[:300]
            for warning in item.get("warnings", [])
            if isinstance(warning, str)
        )
    for failure in dependency_failures or []:
        warnings.append(
            f"{failure.get('agent_id', 'agent')} unavailable: "
            f"{failure.get('error_category', 'agent_dependency_failed')}"
        )
    payload = {
        "question": question[:1500],
        "findings": findings,
        "evidence": evidence,
        "recommendations": recommendations,
        "warnings": list(dict.fromkeys(warnings))[:12],
    }
    _shrink_composition_payload(
        payload,
        max(settings.ctv_one_agent_composition_max_total_chars, 1000),
    )
    return payload


def _concise_result_content(agent_id: str, output: dict[str, Any], limit: int) -> str:
    if agent_id == "knowledge_agent":
        return f"Approved knowledge sources retrieved: {int(output.get('source_count') or 0)}."
    if agent_id == "operations_agent":
        parts = [str(output.get("summary") or "").strip()]
        parts.append(
            f"Tasks: {int(output.get('task_count') or 0)}; "
            f"boards: {int(output.get('board_count') or 0)}."
        )
        if not parts[0]:
            parts[0] = str(output.get("snapshot_context") or "")[: max(limit - 80, 100)]
        return " ".join(part for part in parts if part)[:limit]
    if agent_id == "employee_agent":
        return str(output.get("employee_context") or "")[:limit]
    if agent_id == "reasoning_agent":
        return str(output.get("analysis") or "")[:limit]
    return json.dumps(output, ensure_ascii=True, sort_keys=True)[:limit]


def _shrink_composition_payload(payload: dict[str, Any], maximum: int) -> None:
    def size() -> int:
        return len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))

    while size() > maximum and payload["evidence"]:
        payload["evidence"].pop()
    for group in ("recommendations", "findings"):
        for item in reversed(payload[group]):
            if size() <= maximum:
                return
            item["content"] = item["content"][: max(len(item["content"]) // 2, 100)]
    while size() > maximum and payload["warnings"]:
        payload["warnings"].pop()


def deterministic_composition(payload: dict[str, Any]) -> str:
    sections: list[str] = []
    findings = [item["content"] for item in payload["findings"] if item["content"]]
    if findings:
        sections.append("Findings\n" + "\n".join(f"- {item}" for item in findings))
    sources = [
        f"- {item['citation']} {item['content']}".strip()
        for item in payload["evidence"]
    ]
    if sources:
        sections.append("Sources\n" + "\n".join(sources))
    recommendations = [
        item["content"] for item in payload["recommendations"] if item["content"]
    ]
    if recommendations:
        sections.append(
            "Recommendations\n" + "\n".join(f"- {item}" for item in recommendations)
        )
    if payload["warnings"]:
        sections.append(
            "Warnings\n" + "\n".join(f"- {item}" for item in payload["warnings"])
        )
    return "\n\n".join(sections).strip()


def requires_llm_composition(question: str, payload: dict[str, Any]) -> bool:
    normalized = question.casefold()
    return bool(payload["recommendations"]) or any(
        term in normalized for term in NATURAL_SYNTHESIS_TERMS
    )


class ReasoningAgent(LifecycleAgent):
    definition = AgentDefinition(
        agent_id="reasoning_agent",
        name="Reasoning Agent",
        description="Reasons only over validated outputs from other agents.",
        capabilities=frozenset(
            {"compare", "synthesize", "recommend", "risk_analysis", "tradeoff_analysis"}
        ),
        supported_intents=frozenset({"mixed", "operations", "policy", "employee"}),
        required_permissions=frozenset({"reasoning.use"}),
        input_schema="ValidatedAgentOutputsV1",
        output_schema="ReasoningSummaryV1",
        estimated_cost_class="reasoning",
        supports_parallel_execution=False,
        version="2.0.0",
        required_dependencies=frozenset(
            {DependencyIdentifier.INFERENCE_QUEUE, DependencyIdentifier.OLLAMA_CLIENT}
        ),
        default_budget=AgentExecutionBudget(
            timeout_seconds=settings.ctv_one_agent_reasoning_timeout_seconds,
            max_inference_calls=1,
            max_retrieval_calls=0,
            cost_class="reasoning",
        ),
        default_timeout_seconds=settings.ctv_one_agent_reasoning_timeout_seconds,
        max_timeout_seconds=settings.ctv_one_agent_reasoning_timeout_seconds,
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        dependency_failures = task.inputs.get("dependency_failures", [])
        payload = bounded_composition_context(
            context.question,
            _dependency_payload(task),
            dependency_failures,
        )
        serialized_payload = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        _record_metric(
            context.instrumentation,
            "agent_reasoning_context_chars",
            len(serialized_payload),
        )
        answer = await invoke_agent_model(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze only the supplied structured enterprise evidence. Separate facts, "
                        "recommendations, risks, and warnings. Do not reveal hidden reasoning."
                    ),
                },
                {"role": "user", "content": serialized_payload},
            ],
            model_name=settings.ctv_one_model_reasoning or settings.ollama_model,
            model_role="reasoning",
            agent_id=self.definition.agent_id,
            inference_timeout_seconds=settings.ctv_one_agent_reasoning_timeout_seconds,
            context=context,
        )
        return _result(task, started, output={"analysis": answer[:6000]})


class ResponseComposerAgent(LifecycleAgent):
    definition = AgentDefinition(
        agent_id="response_composer_agent",
        name="Response Composer Agent",
        description="Composes a final answer from validated structured results.",
        capabilities=frozenset({"executive_summary", "final_answer", "structured_brief"}),
        supported_intents=frozenset({"mixed", "operations", "policy", "employee", "general"}),
        required_permissions=frozenset({"compose.use"}),
        input_schema="ValidatedAgentOutputsV1",
        output_schema="CompanyBrainAnswerV1",
        estimated_cost_class="standard",
        supports_parallel_execution=False,
        version="2.0.0",
        required=True,
        required_dependencies=frozenset(
            {DependencyIdentifier.INFERENCE_QUEUE, DependencyIdentifier.OLLAMA_CLIENT}
        ),
        default_budget=AgentExecutionBudget(
            timeout_seconds=settings.ctv_one_agent_composer_timeout_seconds,
            max_inference_calls=1,
            max_retrieval_calls=0,
            allow_partial=False,
        ),
        default_timeout_seconds=settings.ctv_one_agent_composer_timeout_seconds,
        max_timeout_seconds=settings.ctv_one_agent_composer_timeout_seconds,
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        dependency_failures = task.inputs.get("dependency_failures", [])
        payload = bounded_composition_context(
            context.question,
            _dependency_payload(task),
            dependency_failures,
        )
        serialized_payload = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        _record_metric(
            context.instrumentation,
            "agent_composer_context_chars",
            len(serialized_payload),
        )
        _record_metric(
            context.instrumentation,
            "agent_composer_context_evidence_items",
            len(payload["evidence"]),
        )
        if dependency_failures or not requires_llm_composition(context.question, payload):
            answer = deterministic_composition(payload)
            strategy = (
                "fallback_deterministic" if dependency_failures else "deterministic"
            )
            _record_metric(context.instrumentation, "composition_strategy", strategy)
            return _result(
                task,
                started,
                output={"answer": answer[:12000]},
                warnings=payload["warnings"],
                composition_strategy=strategy,
            )
        _record_metric(context.instrumentation, "composition_strategy", "llm")
        answer = await invoke_agent_model(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Compose a concise Company Brain answer using only supplied validated "
                        "results. Preserve citation labels. Clearly distinguish retrieved facts "
                        "from recommendations "
                        "and warnings. Never mention internal planning or hidden reasoning."
                    ),
                },
                {
                    "role": "user",
                    "content": serialized_payload,
                },
            ],
            model_name=(
                settings.ctv_one_model_balanced
                or settings.ctv_one_model_default
                or settings.ollama_model
            ),
            model_role="balanced",
            agent_id=self.definition.agent_id,
            inference_timeout_seconds=settings.ctv_one_agent_composer_timeout_seconds,
            context=context,
        )
        return _result(
            task,
            started,
            output={"answer": answer[:12000]},
            warnings=payload["warnings"],
            composition_strategy="llm",
        )


def build_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    BuiltinCoreAgentPlugin().register(registry, registry.catalog)
    return registry


class BuiltinCoreAgentPlugin:
    plugin = AgentPlugin(
        plugin_id="ctv_one_core_agents",
        version="2.0.0",
        required_runtime_contract="1.0",
    )

    def register(self, registry: AgentRegistry, catalog: CapabilityCatalog) -> None:
        for agent in (
            KnowledgeAgent(),
            OperationsAgent(),
            EmployeeAgent(),
            ReasoningAgent(),
            ResponseComposerAgent(),
        ):
            registry.register(agent)
