import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.context_requirements import ContextRequirements


@dataclass(frozen=True)
class RouteDecision:
    intent: str
    confidence: float
    use_employee_context: bool
    use_operations: bool
    collections: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    context_requirements: ContextRequirements = field(
        default_factory=ContextRequirements
    )


RULES: dict[str, tuple[set[str], list[str], bool]] = {
    "operations": (
        {
            "task", "tasks", "deadline", "deadlines", "due", "overdue",
            "priority", "priorities", "prioritize", "operation", "operations",
            "operational", "status", "board", "boards",
            "workload", "project", "projects", "today", "tomorrow",
            "stuck", "blocked", "critical", "urgent", "focus",
        },
        [],
        True,
    ),
    "policy": (
        {
            "policy", "policies", "leave", "attendance", "absence", "absent",
            "benefit", "benefits", "overtime", "holiday", "conduct",
            "discipline", "wfh", "work from home", "dress code",
        },
        ["company-policies", "hr-policies"],
        False,
    ),
    "equipment": (
        {
            "camera", "sony", "fx3", "a7", "a74", "a7iv", "dji",
            "drone", "light", "lighting", "audio", "microphone",
            "printer", "firmware", "battery", "lens", "equipment",
            "manual", "manuals",
        },
        ["equipment-manuals", "technical-documentation"],
        False,
    ),
    "production": (
        {
            "shoot", "shooting", "ingest", "editing", "edit", "render",
            "archive", "delivery", "footage", "nas", "export",
            "multicam", "backup", "production", "sop", "sops",
        },
        ["production-sops", "technical-documentation"],
        False,
    ),
    "branding": (
        {
            "brand", "branding", "logo", "font", "fonts", "color",
            "colors", "proposal", "presentation", "pitch", "tone",
            "marketing", "visual identity", "brand guideline",
            "brand guidelines", "project reference", "project references",
            "reference", "references",
        },
        ["brand-guidelines", "project-references"],
        False,
    ),
    "training": (
        {
            "training", "tutorial", "learn", "onboarding", "guide",
            "how do i", "how to", "teach", "lesson", "knowledge",
        },
        ["training-materials", "equipment-manuals"],
        False,
    ),
    "technical": (
        {
            "network", "server", "qdrant", "postgres", "ollama",
            "infrastructure", "router", "switch", "database", "api",
            "docker", "windows", "software", "system", "troubleshoot",
            "troubleshooting", "technical issue", "technical issues",
        },
        ["technical-documentation"],
        False,
    ),
    "employee": (
        {
            "my workload", "my tasks", "my projects", "my skills",
            "my tools", "my role", "my responsibilities", "preference",
            "preferences",
        },
        [],
        True,
    ),
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _matches(text: str, terms: set[str]) -> int:
    normalized = f" {_normalize(text)} "
    return sum(1 for term in terms if f" {_normalize(term)} " in normalized)


def _has_any(text: str, terms: set[str]) -> bool:
    return _matches(text, terms) > 0


EMPLOYEE_TERMS = {
    "my role",
    "my preferences",
    "my preference",
    "role and preferences",
    "assigned to me",
    "owner",
    "ownership",
    "assignee",
    "my workload",
    "my tasks",
    "my projects",
}

OPERATIONAL_TERMS = {
    "task",
    "tasks",
    "deadline",
    "deadlines",
    "due",
    "overdue",
    "priority",
    "priorities",
    "prioritize",
    "operation",
    "operations",
    "operational",
    "status",
    "board",
    "boards",
    "workload",
    "project",
    "projects",
    "today",
    "tomorrow",
    "stuck",
    "blocked",
    "critical",
    "urgent",
}

KNOWLEDGE_TERMS = {
    "approved",
    "knowledge",
    "policy",
    "manual",
    "sop",
    "guidance",
    "documentation",
    "reference",
    "sources",
}


def _context_requirements(
    *,
    question: str,
    intent: str,
    collections: list[str],
    use_operations: bool,
) -> ContextRequirements:
    explicit_employee = _has_any(question, EMPLOYEE_TERMS)
    explicit_operations = _has_any(question, OPERATIONAL_TERMS)
    explicit_knowledge = _has_any(question, KNOWLEDGE_TERMS)

    include_operations = use_operations
    include_knowledge = bool(collections)
    selected_collections = list(collections)

    if use_operations and explicit_knowledge and not selected_collections:
        include_knowledge = True
        selected_collections = [
            "company-policies",
            "production-sops",
            "technical-documentation",
        ]

    if intent == "employee":
        include_operations = explicit_operations
        include_knowledge = explicit_knowledge and bool(selected_collections)

    include_employee = explicit_employee
    if intent == "employee":
        include_employee = True
    elif intent in {"policy", "equipment", "production", "technical", "branding"}:
        include_employee = False
    elif intent == "operations":
        include_employee = explicit_employee and not _has_any(
            question,
            {"overdue", "late", "past due"},
        )

    return ContextRequirements(
        include_knowledge=include_knowledge,
        include_operations=include_operations,
        include_employee=include_employee,
        include_history=False,
        include_system_instructions=True,
        knowledge_collections=selected_collections,
        max_knowledge_chunks=settings.company_brain_max_knowledge_chunks,
        max_knowledge_chars=settings.company_brain_max_knowledge_chars,
        max_operational_tasks=settings.company_brain_max_operational_tasks,
        max_operational_chars=settings.company_brain_max_operational_chars,
        max_employee_context_chars=settings.company_brain_max_employee_chars,
        max_history_messages=settings.company_brain_max_history_messages,
        max_history_chars=settings.company_brain_max_history_chars,
        max_total_prompt_chars=settings.company_brain_max_total_prompt_chars,
    )


class IntelligenceRouter:
    def route(self, question: str) -> RouteDecision:
        scores: list[tuple[str, int, list[str], bool]] = []

        for intent, (terms, collections, operations) in RULES.items():
            score = _matches(question, terms)
            if score:
                scores.append((intent, score, collections, operations))

        if not scores:
            requirements = _context_requirements(
                question=question,
                intent="general",
                collections=[],
                use_operations=False,
            )
            return RouteDecision(
                intent="general",
                confidence=0.45,
                use_employee_context=requirements.include_employee,
                use_operations=False,
                collections=[],
                sources=requirements.selected_context_types(),
                context_requirements=requirements,
            )

        scores.sort(key=lambda item: item[1], reverse=True)
        top_score = scores[0][1]
        winners = [item for item in scores if item[1] == top_score]

        if len(winners) > 1:
            collections: list[str] = []
            use_operations = False
            sources = ["employee-context"]

            for _, _, selected, operational in winners:
                for collection in selected:
                    if collection not in collections:
                        collections.append(collection)
                use_operations = use_operations or operational

            if collections:
                sources.append("knowledge-center")
            if use_operations:
                sources.append("monday.com")

            requirements = _context_requirements(
                question=question,
                intent="mixed",
                collections=collections,
                use_operations=use_operations,
            )
            return RouteDecision(
                intent="mixed",
                confidence=min(0.9, 0.65 + top_score * 0.05),
                use_employee_context=requirements.include_employee,
                use_operations=requirements.include_operations,
                collections=requirements.knowledge_collections,
                sources=sources,
                context_requirements=requirements,
            )

        intent, score, collections, use_operations = winners[0]
        confidence = min(0.98, 0.70 + score * 0.06)

        requirements = _context_requirements(
            question=question,
            intent=intent,
            collections=collections,
            use_operations=use_operations,
        )
        sources = requirements.selected_context_types()

        return RouteDecision(
            intent=intent,
            confidence=confidence,
            use_employee_context=requirements.include_employee,
            use_operations=requirements.include_operations,
            collections=requirements.knowledge_collections,
            sources=sources,
            context_requirements=requirements,
        )


intelligence_router = IntelligenceRouter()
