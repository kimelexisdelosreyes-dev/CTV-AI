from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_registry import MODEL_REGISTRY
from app.core.prompts import ASSISTANT_PROMPTS
from app.db.models.orchestrator_event import OrchestratorEvent
from app.schemas.orchestrator import RouteDecision
from app.services.intent_router import intent_router
from app.services.ollama_service import ollama_service


class OrchestratorService:
    async def decide(
        self,
        message: str,
        override: str = "auto",
    ) -> RouteDecision:
        intent = intent_router.route(message, override)
        profile = MODEL_REGISTRY[intent.assistant]

        available_models = await ollama_service.list_models()
        selected_model = profile.ollama_model

        if selected_model not in available_models:
            fallback = MODEL_REGISTRY["general"].ollama_model
            selected_model = fallback
            reason = (
                f"{intent.reason}; configured model unavailable, "
                f"falling back to {fallback}"
            )
        else:
            reason = intent.reason

        return RouteDecision(
            assistant=intent.assistant,
            model=selected_model,
            confidence=intent.confidence,
            reason=reason,
        )

    async def chat(
        self,
        message: str,
        conversation: list[dict[str, str]],
        override: str,
        user_email: str,
        db: AsyncSession,
    ) -> tuple[str, RouteDecision]:
        route = await self.decide(message, override)
        prompt_key = (
            route.assistant
            if route.assistant in ASSISTANT_PROMPTS
            else "general"
        )

        messages = [
            {
                "role": "system",
                "content": ASSISTANT_PROMPTS[prompt_key].strip(),
            },
            *[
                item
                for item in conversation
                if item.get("role") in {"user", "assistant"}
                and item.get("content")
            ],
            {"role": "user", "content": message},
        ]

        response = await ollama_service.chat(
            messages=messages,
            model=route.model,
        )

        db.add(
            OrchestratorEvent(
                user_email=user_email,
                message_preview=message[:500],
                selected_assistant=route.assistant,
                selected_model=route.model,
                confidence=route.confidence,
                reason=route.reason,
            )
        )
        await db.commit()

        return response, route


orchestrator_service = OrchestratorService()
