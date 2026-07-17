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
