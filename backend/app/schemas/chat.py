from typing import Literal

from pydantic import BaseModel, Field

AssistantName = Literal["general", "production", "graphics", "drone", "it"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    assistant: AssistantName = "general"


class ChatResponse(BaseModel):
    response: str
    assistant: AssistantName
