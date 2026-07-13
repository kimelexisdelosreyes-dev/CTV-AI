from typing import Literal

from pydantic import BaseModel, Field

HumorLevel = Literal["light", "spicy", "roast_me", "team_banter", "burnout_break"]


class ComedyProfileUpdate(BaseModel):
    preferred_language: str = Field(default="English", max_length=50)
    humor_level: HumorLevel = "light"
    likes: list[str] = Field(default_factory=list, max_length=30)
    safe_roast_topics: list[str] = Field(default_factory=list, max_length=30)
    off_limit_topics: list[str] = Field(default_factory=list, max_length=30)
    consent_to_roasting: bool = False


class ComedyProfilePublic(ComedyProfileUpdate):
    user_email: str
