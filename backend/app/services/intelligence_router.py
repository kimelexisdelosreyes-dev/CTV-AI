from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteDecision:
    intent: str
    confidence: float
    use_employee_context: bool
    use_operations: bool
    collections: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


RULES: dict[str, tuple[set[str], list[str], bool]] = {
    "operations": (
        {
            "task", "tasks", "deadline", "deadlines", "due", "overdue",
            "priority", "prioritize", "status", "board", "boards",
            "workload", "project", "projects", "today", "tomorrow",
            "stuck", "blocked", "critical", "urgent", "focus",
        },
        [],
        True,
    ),
    "policy": (
        {
            "policy", "leave", "attendance", "absence", "absent",
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
            "printer", "firmware", "battery", "lens",
        },
        ["equipment-manuals", "technical-documentation"],
        False,
    ),
    "production": (
        {
            "shoot", "shooting", "ingest", "editing", "edit", "render",
            "archive", "delivery", "footage", "nas", "export",
            "multicam", "backup", "production",
        },
        ["production-sops", "technical-documentation"],
        False,
    ),
    "branding": (
        {
            "brand", "branding", "logo", "font", "fonts", "color",
            "colors", "proposal", "presentation", "pitch", "tone",
            "marketing", "visual identity",
        },
        ["brand-guidelines", "project-references"],
        False,
    ),
    "training": (
        {
            "training", "tutorial", "learn", "onboarding", "guide",
            "how do i", "how to", "teach", "lesson",
        },
        ["training-materials", "equipment-manuals"],
        False,
    ),
    "technical": (
        {
            "network", "server", "qdrant", "postgres", "ollama",
            "infrastructure", "router", "switch", "database", "api",
            "docker", "windows", "software", "system",
        },
        ["technical-documentation"],
        False,
    ),
    "employee": (
        {
            "my workload", "my tasks", "my projects", "my skills",
            "my tools", "my role", "my responsibilities",
        },
        [],
        True,
    ),
}


def _matches(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


class IntelligenceRouter:
    def route(self, question: str) -> RouteDecision:
        scores: list[tuple[str, int, list[str], bool]] = []

        for intent, (terms, collections, operations) in RULES.items():
            score = _matches(question, terms)
            if score:
                scores.append((intent, score, collections, operations))

        if not scores:
            return RouteDecision(
                intent="general",
                confidence=0.45,
                use_employee_context=True,
                use_operations=False,
                collections=[],
                sources=["employee-context", "knowledge-center"],
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

            return RouteDecision(
                intent="mixed",
                confidence=min(0.9, 0.65 + top_score * 0.05),
                use_employee_context=True,
                use_operations=use_operations,
                collections=collections,
                sources=sources,
            )

        intent, score, collections, use_operations = winners[0]
        confidence = min(0.98, 0.70 + score * 0.06)

        sources = ["employee-context"]
        if collections:
            sources.append("knowledge-center")
        if use_operations:
            sources.append("monday.com")

        return RouteDecision(
            intent=intent,
            confidence=confidence,
            use_employee_context=True,
            use_operations=use_operations,
            collections=collections,
            sources=sources,
        )


intelligence_router = IntelligenceRouter()
