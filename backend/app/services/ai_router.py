from app.core.prompts import ASSISTANT_PROMPTS
from app.atlas.bootstrap import atlas_shadow_mode_service
from app.shadow_mode import production_prompt_from_messages, shadow_request_id
from app.schemas.chat import AssistantName
from app.services.ollama_service import ollama_service

MODEL_TO_ASSISTANT: dict[str, str] = {
    "ctv-ai-general": "general",
    "ctv-ai-production": "production",
    "ctv-ai-graphics": "graphics",
    "ctv-ai-drone": "drone",
    "ctv-ai-it": "it",
    "ctv-ai-comedy": "comedy",
}


class AIRouter:
    @staticmethod
    def supported_models() -> list[str]:
        return ["ctv-ai-auto", *MODEL_TO_ASSISTANT]

    @staticmethod
    def assistant_for_model(model: str) -> str:
        return MODEL_TO_ASSISTANT.get(model, "general")

    @staticmethod
    def build_messages(
        messages: list[dict[str, str]],
        assistant: str,
    ) -> list[dict[str, str]]:
        system_prompt = ASSISTANT_PROMPTS[assistant].strip()
        filtered_messages = [
            message for message in messages if message.get("role") != "system"
        ]
        return [{"role": "system", "content": system_prompt}, *filtered_messages]

    async def chat(
        self,
        message: str,
        assistant: AssistantName,
        *,
        user_identifier: str | None = None,
    ) -> str:
        messages = self.build_messages(
            [{"role": "user", "content": message}],
            assistant,
        )
        production_prompt = production_prompt_from_messages(messages)
        routed_messages, _, _ = await atlas_shadow_mode_service.route_messages(
            messages=messages,
            request_id=shadow_request_id(production_prompt),
            user_identifier=user_identifier,
            intent=f"chat_{assistant}",
        )
        return await ollama_service.chat(routed_messages)


ai_router = AIRouter()
