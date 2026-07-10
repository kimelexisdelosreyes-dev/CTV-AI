from app.core.prompts import ASSISTANT_PROMPTS
from app.schemas.chat import AssistantName
from app.services.ollama_service import ollama_service

MODEL_TO_ASSISTANT: dict[str, AssistantName] = {
    "ctv-ai-general": "general",
    "ctv-ai-production": "production",
    "ctv-ai-graphics": "graphics",
    "ctv-ai-drone": "drone",
    "ctv-ai-it": "it",
}


class AIRouter:
    @staticmethod
    def supported_models() -> list[str]:
        return list(MODEL_TO_ASSISTANT)

    @staticmethod
    def assistant_for_model(model: str) -> AssistantName:
        return MODEL_TO_ASSISTANT.get(model, "general")

    @staticmethod
    def build_messages(
        messages: list[dict[str, str]],
        assistant: AssistantName,
    ) -> list[dict[str, str]]:
        system_prompt = ASSISTANT_PROMPTS[assistant].strip()
        filtered_messages = [
            message for message in messages if message.get("role") != "system"
        ]
        return [{"role": "system", "content": system_prompt}, *filtered_messages]

    async def chat(self, message: str, assistant: AssistantName) -> str:
        messages = self.build_messages(
            [{"role": "user", "content": message}],
            assistant,
        )
        return await ollama_service.chat(messages)


ai_router = AIRouter()
