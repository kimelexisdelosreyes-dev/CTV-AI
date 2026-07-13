from app.services.intent_router import intent_router


def test_routes_comedy_for_roast() -> None:
    result = intent_router.route("Roast me, I am burned out")
    assert result.assistant == "comedy"


def test_routes_comedy_for_burnout_break() -> None:
    result = intent_router.route("Give me a funny burnout break")
    assert result.assistant == "comedy"


def test_manual_comedy_override() -> None:
    result = intent_router.route("Anything", override="comedy")
    assert result.assistant == "comedy"
    assert result.confidence == 1.0
