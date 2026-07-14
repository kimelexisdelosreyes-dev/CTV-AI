from pydantic import BaseModel, Field


class ContextMetadata(BaseModel):
    applied: bool = False
    job_title: str | None = None
    experience_level: str | None = None
    preferred_language: str | None = None
    response_style: str | None = None
    detail_level: str | None = None

    skills_used: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    memories_used: int = 0

    operational_context_applied: bool = False
    operational_tasks_used: int = 0
    operational_boards_used: int = 0
    operational_summary: str | None = None

    routed_intent: str = "general"
    routing_confidence: float = 0.0
    routed_collections: list[str] = Field(default_factory=list)
    intelligence_sources: list[str] = Field(default_factory=list)


class ContextBundle(BaseModel):
    system_context: str
    metadata: ContextMetadata