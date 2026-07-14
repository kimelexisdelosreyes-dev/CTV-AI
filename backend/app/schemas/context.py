from pydantic import BaseModel


class ContextMetadata(BaseModel):
    applied: bool = False
    job_title: str | None = None
    experience_level: str | None = None
    preferred_language: str | None = None
    response_style: str | None = None
    detail_level: str | None = None
    skills_used: list[str] = []
    tools_used: list[str] = []
    memories_used: int = 0


class ContextBundle(BaseModel):
    system_context: str
    metadata: ContextMetadata
