from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.manager import connector_manager
from app.db.models.employee import MemoryStatus
from app.db.models.user import User
from app.schemas.context import ContextBundle, ContextMetadata
from app.services import employee_service


class ContextEngine:
    async def build_employee_context(
        self,
        db: AsyncSession,
        user: User,
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

        memory_lines = (
            "\n".join(
                f"- {memory.memory_type}: {memory.content}"
                for memory in active_memories
            )
            or "- None"
        )

        connector_names = [
            descriptor.name
            for descriptor in connector_manager.descriptors()
            if descriptor.enabled
        ]

        context = f"""
EMPLOYEE CONTEXT

Identity
- Name: {user.full_name}
- Account role: {user.role.value}
- Job title: {profile.job_title or "Not set"}
- Experience level: {profile.experience_level.value}

Responsibilities
- Primary responsibilities: {profile.primary_responsibilities or "Not set"}
- Specialties: {profile.specialties or "Not set"}

Communication preferences
- Preferred language: {profile.preferred_language}
- Response style: {profile.response_style.value}
- Detail level: {profile.detail_level.value}
- Prefers checklists: {preferences.prefers_checklists}
- Prefers visual examples: {preferences.prefers_visual_examples}
- Comfortable with technical terms: {preferences.comfortable_with_technical_terms}
- Preferred output format: {preferences.preferred_output_format}
- Approval restrictions: {preferences.requires_approval_for or "None"}
- Custom instructions: {preferences.custom_instructions or "None"}

Skills
- {", ".join(skill_names) if skill_names else "None recorded"}

Tools
- {", ".join(tool_names) if tool_names else "None recorded"}

Confirmed work memories
{memory_lines}

Available enterprise connectors
- {", ".join(connector_names) if connector_names else "None registered"}

Personalization rules
- Adapt wording and depth to the employee's experience.
- Follow the employee's response style and output preferences.
- Use tools and skills only when relevant.
- Never invent employee traits or psychological conclusions.
- Do not override company policy or source-grounding requirements.
""".strip()

        return ContextBundle(
            system_context=context,
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
            ),
        )


context_engine = ContextEngine()
