import uuid
from types import SimpleNamespace

import pytest

from app.db.models.conversation import ConversationMessageRole
from app.services import conversation_service
from app.services.conversation_service import safe_message_content, title_from_prompt


def test_title_from_prompt_is_deterministic_and_trimmed() -> None:
    assert title_from_prompt("  What   should   we prioritize today?  ") == (
        "What should we prioritize today?"
    )


def test_title_from_prompt_limits_length_without_hidden_context() -> None:
    title = title_from_prompt("x" * 200)

    assert len(title) <= 64
    assert title.endswith("...")


def test_safe_message_content_caps_visible_text() -> None:
    content = safe_message_content("x" * 25_000)

    assert len(content) == 20_000


@pytest.mark.anyio
async def test_client_message_id_makes_user_append_idempotent(monkeypatch) -> None:
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()
    existing = SimpleNamespace(
        id=message_id,
        conversation_id=conversation_id,
        role=ConversationMessageRole.user,
        content="Visible question",
    )

    class FakeDb:
        async def get(self, _model, item_id):
            assert item_id == message_id
            return existing

    async def owned(*_):
        return SimpleNamespace(id=conversation_id)

    monkeypatch.setattr(conversation_service, "get_owned_conversation", owned)
    result = await conversation_service.append_message(
        FakeDb(),
        SimpleNamespace(),
        conversation_id,
        role=ConversationMessageRole.user,
        content="Visible question",
        message_id=message_id,
    )

    assert result is existing
