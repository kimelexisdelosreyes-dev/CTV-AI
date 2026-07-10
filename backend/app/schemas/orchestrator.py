from typing import Literal

from pydantic import BaseModel, Field

AssistantOverride = Literal[
    "auto",
    "general",
    "production",
    "graphics",
    "drone",
    "it",
    "coder",
]


class RouteRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    assistant: AssistantOverride = "auto"


class RouteDecision(BaseModel):
    assistant: str
    model: str
    confidence: float
    reason: str


class OrchestratedChatRequest(RouteRequest):
    conversation: list[dict[str, str]] = []


class OrchestratedChatResponse(BaseModel):
    response: str
    route: RouteDecision
