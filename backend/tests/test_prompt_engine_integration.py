import pytest

from app.ai_runtime import RuntimeMessage
from app.core.prompts import ASSISTANT_PROMPTS
from app.prompt_engine import PromptCompositionRequest, PromptMessage, default_prompt_composer
from app.services.ai_router import AIRouter


def legacy(messages, assistant):
    return [{"role": "system", "content": ASSISTANT_PROMPTS[assistant].strip()}, *(message for message in messages if message.get("role") != "system")]


@pytest.mark.parametrize("messages", [
    [{"role": "user", "content": "one"}],
    [{"role": "system", "content": "ignored"}, {"role": "user", "content": "one"}],
    [{"role": "user", "content": "first"}, {"role": "assistant", "content": "answer"}, {"role": "user", "content": "final"}],
    [{"role": "system", "content": "a"}, {"role": "system", "content": "b"}, {"role": "user", "content": "  keep  \nline\n"}],
    [{"role": "assistant", "content": "å›žå¤"}, {"role": "user", "content": "ä½ å¥½ðŸ‘‹\n\n  whitespace  "}],
    [{"role": "user", "content": ""}],
    [],
])
def test_composer_matches_exact_legacy_messages(messages):
    assert AIRouter.build_messages(messages, "general") == legacy(messages, "general")


def test_long_history_metadata_and_model_id_are_preserved():
    messages = [{"role": "user" if index % 2 == 0 else "assistant", "content": f"turn {index}\n", "tag": str(index)} for index in range(40)]
    result = default_prompt_composer().compose(PromptCompositionRequest(messages[-1]["content"], conversation_history=tuple(PromptMessage(item["role"], item["content"], (("tag", item["tag"]),)) for item in messages[:-1]), selected_model_id="deepseek-r1:14b", final_metadata=(("tag", "39"),), assistant="general"))
    assert result.messages[-1].content == messages[-1]["content"] and result.metadata == ()
    assert result.messages[1].metadata == (("tag", "0"),)


@pytest.mark.asyncio
async def test_airouter_composes_once_and_atlas_receives_exact_messages():
    class Composer:
        def __init__(self): self.calls = 0; self.delegate = default_prompt_composer()
        def compose(self, request): self.calls += 1; return self.delegate.compose(request)
    class Shadow:
        async def route_messages(self, *, messages, **kwargs): self.messages = messages; return messages, None, None
    class Service:
        async def chat(self, messages, **kwargs): self.messages = messages; return "ok"
    composer, shadow, service = Composer(), Shadow(), Service()
    router = AIRouter(prompt_composer=composer, shadow_service=shadow, ollama=service, runtime_enabled=False)
    assert await router.chat("hello  \n", "general") == "ok"
    assert composer.calls == 1 and shadow.messages == service.messages == legacy([{"role": "user", "content": "hello  \n"}], "general")


def test_runtime_message_conversion_is_exact_for_composed_output():
    messages = AIRouter.build_messages([{"role": "user", "content": "line one\n  line two"}], "general")
    converted = tuple(RuntimeMessage(message["role"], message["content"]) for message in messages)
    assert [(message.role, message.content) for message in converted] == [(message["role"], message["content"]) for message in messages]
