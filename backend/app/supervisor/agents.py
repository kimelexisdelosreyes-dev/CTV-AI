from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.context_engine import context_engine
from app.services.inference_queue import inference_queue
from app.services.ollama_service import ollama_service
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
    user: Any
    db: Any
    question: str
    top_k: int
    route: Any
    requirements: Any
    instrumentation: Any
    knowledge_fetcher: Any


def _result(
    task: AgentTask,
    started: float,
    *,
    output: dict[str, Any],
    evidence: list[EvidenceItem] | None = None,
    warnings: list[str] | None = None,
) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        agent_id=task.agent_id,
        status="success",
        structured_output=output,
        evidence=evidence or [],
        warnings=warnings or [],
        duration_ms=round((perf_counter() - started) * 1000, 3),
    )


async def invoke_agent_model(
    *,
    messages: list[dict[str, str]],
    model_name: str,
    model_role: str,
    context: AgentExecutionContext,
) -> str:
    if context.instrumentation:
        context.instrumentation.model_name = model_name
        context.instrumentation.record_metric("model_selected", model_name)
    admission = await inference_queue.submit(
        request_id=getattr(context.instrumentation, "request_id", None),
        user_id=str(context.user.id),
        model_name=model_name,
        model_role=model_role,
        streaming=False,
        estimated_cost_class=model_role,
    )
    inference_queue.record_result(context.instrumentation, admission.initial_result)
    lease = await admission.wait()
    inference_queue.record_lease(context.instrumentation, lease)
    cancelled = False
    try:
        async with asyncio.timeout(settings.ctv_one_supervisor_task_timeout_seconds):
            return await ollama_service.chat(messages, model=model_name)
    except asyncio.CancelledError:
        cancelled = True
        raise
    finally:
        await lease.release(cancelled=cancelled)


class KnowledgeAgent:
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


class OperationsAgent:
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


class EmployeeAgent:
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


class ReasoningAgent:
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
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        payload = _dependency_payload(task)
        answer = await invoke_agent_model(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze only the supplied structured enterprise evidence. Separate facts, "
                        "recommendations, risks, and warnings. Do not reveal hidden reasoning."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)[:10000]},
            ],
            model_name=settings.ctv_one_model_reasoning or settings.ollama_model,
            model_role="reasoning",
            context=context,
        )
        return _result(task, started, output={"analysis": answer[:6000]})


class ResponseComposerAgent:
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
    )

    async def execute(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        started = perf_counter()
        payload = _dependency_payload(task)
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
                    "content": json.dumps(
                        {"question": context.question, "results": payload},
                        ensure_ascii=True,
                    )[:12000],
                },
            ],
            model_name=(
                settings.ctv_one_model_balanced
                or settings.ctv_one_model_default
                or settings.ollama_model
            ),
            model_role="balanced",
            context=context,
        )
        return _result(task, started, output={"answer": answer[:12000]})


def build_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    for agent in (
        KnowledgeAgent(),
        OperationsAgent(),
        EmployeeAgent(),
        ReasoningAgent(),
        ResponseComposerAgent(),
    ):
        registry.register(agent)
    return registry
