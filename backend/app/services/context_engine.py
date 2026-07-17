from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.employee import MemoryStatus
from app.db.models.user import User
from app.schemas.context import ContextBundle, ContextMetadata
from app.services import employee_service
from app.services.intelligence_router import RouteDecision
from app.services.operations_context_service import operations_context_service
from app.services.performance_instrumentation import AskPerformanceInstrumentation


def _question_mentions(question: str | None, terms: set[str]) -> bool:
    normalized = f" {(question or '').lower()} "
    return any(term in normalized for term in terms)


def _cap_text(value: str, max_chars: int | None) -> tuple[str, bool]:
    if not max_chars or max_chars <= 0 or len(value) <= max_chars:
        return value, False
    if max_chars <= 20:
        return value[:max_chars], True
    return value[: max_chars - 15].rstrip() + "\n[Truncated]", True


class ContextEngine:
    async def build_employee_context(
        self,
        db: AsyncSession,
        user: User,
        question: str | None = None,
        route: RouteDecision | None = None,
        instrumentation: AskPerformanceInstrumentation | None = None,
        include_operations: bool | None = None,
        max_employee_context_chars: int | None = None,
    ) -> ContextBundle:
        profile = await employee_service.ensure_profile(db, user)
        preferences = await employee_service.ensure_preferences(db, user)
        skills = await employee_service.list_skills(db, user)
        tools = await employee_service.list_tools(db, user)
        memories = await employee_service.list_memories(db, user)

        active_memories = [
            memory
            for memory in memories
            if memory.status == MemoryStatus.confirmed
            and (
                memory.expires_at is None
                or memory.expires_at > datetime.now(timezone.utc)
            )
        ]

        skill_names = [skill.name for skill in skills]
        tool_names = [tool.name for tool in tools]

        include_work_profile = _question_mentions(
            question,
            {" role ", " responsibility", " responsibilities", " focus ", " next "},
        )
        include_preferences = _question_mentions(
            question,
            {" preference", " preferences", " style", " language", " format"},
        )
        include_skills = _question_mentions(
            question,
            {" skill", " skills", " tool", " tools", " capability"},
        )
        include_memories = _question_mentions(
            question,
            {" memory", " memories", " remember", " remembered"},
        )

        should_include_operations = (
            bool(route and route.use_operations)
            if include_operations is None
            else include_operations
        )
        if instrumentation:
            with instrumentation.measure("operational_context"):
                operations = await operations_context_service.build(
                    question or "",
                    force=should_include_operations,
                )
        else:
            operations = await operations_context_service.build(
                question or "",
                force=should_include_operations,
            )

        employee_lines = [
            "EMPLOYEE CONTEXT",
            f"- Name: {user.full_name}",
            f"- Account role: {user.role.value}",
            f"- Job title: {profile.job_title or 'Not set'}",
            f"- Experience level: {profile.experience_level.value}",
        ]

        if include_work_profile:
            employee_lines.extend(
                [
                    f"- Primary responsibilities: {profile.primary_responsibilities or 'Not set'}",
                    f"- Specialties: {profile.specialties or 'Not set'}",
                ]
            )

        if include_preferences:
            employee_lines.extend(
                [
                    f"- Preferred language: {profile.preferred_language}",
                    f"- Response style: {profile.response_style.value}",
                    f"- Detail level: {profile.detail_level.value}",
                    f"- Prefers checklists: {preferences.prefers_checklists}",
                    f"- Preferred output format: {preferences.preferred_output_format}",
                ]
            )

        if include_skills:
            employee_lines.extend(
                [
                    f"- Skills: {', '.join(skill_names) if skill_names else 'None recorded'}",
                    f"- Tools: {', '.join(tool_names) if tool_names else 'None recorded'}",
                ]
            )

        if include_memories:
            memory_lines = (
                "\n".join(
                    f"- {memory.memory_type}: {memory.content}"
                    for memory in active_memories[:3]
                )
                or "- None"
            )
            employee_lines.extend(["Confirmed work memories", memory_lines])

        employee_context = "\n".join(employee_lines).strip()
        original_employee_chars = len(employee_context)
        employee_context, employee_truncated = _cap_text(
            employee_context,
            max_employee_context_chars,
        )

        system_context = employee_context

        if operations.applied:
            system_context = f"{employee_context}\n\n{operations.text}"

        if instrumentation:
            instrumentation.record_metric(
                "employee_context_original_chars",
                original_employee_chars,
            )
            instrumentation.record_metric(
                "employee_context_final_chars",
                len(employee_context),
            )
            instrumentation.record_metric(
                "operational_context_chars",
                len(operations.text),
            )
            if employee_truncated:
                instrumentation.record_metric("employee_context_truncated", 1)

        return ContextBundle(
            system_context=system_context,
            metadata=ContextMetadata(
                applied=True,
                job_title=profile.job_title,
                experience_level=profile.experience_level.value,
                preferred_language=profile.preferred_language,
                response_style=profile.response_style.value,
                detail_level=profile.detail_level.value,
                skills_used=skill_names,
                tools_used=tool_names,
                memories_used=len(active_memories),
                operational_context_applied=operations.applied,
                operational_tasks_used=operations.task_count,
                operational_boards_used=operations.board_count,
                operational_summary=operations.summary,
                routed_intent=route.intent if route else "general",
                routing_confidence=route.confidence if route else 0.0,
                routed_collections=route.collections if route else [],
                intelligence_sources=route.sources if route else ["employee-context"],
            ),
        )


context_engine = ContextEngine()
