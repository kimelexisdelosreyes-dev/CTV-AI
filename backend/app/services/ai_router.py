from app.core.prompts import ASSISTANT_PROMPTS
from app.schemas.chat import AssistantName
from app.services.ollama_service import ollama_service


class AIRouter:
    async def chat(self, message: str, assistant: AssistantName) -> str:
        system_prompt = ASSISTANT_PROMPTS[assistant]

        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": message},
        ]

        return await ollama_service.chat(messages)


ai_router = AIRouter()
