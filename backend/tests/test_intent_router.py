from app.services.intent_router import intent_router


def test_routes_graphics() -> None:
    result = intent_router.route(
        "Create an Adobe Firefly prompt for a cinematic poster"
    )
    assert result.assistant == "graphics"


def test_routes_it() -> None:
    result = intent_router.route("My NAS is not visible in Windows")
    assert result.assistant == "it"


def test_routes_drone() -> None:
    result = intent_router.route("Create a DJI drone flight plan")
    assert result.assistant == "drone"


def test_routes_production() -> None:
    result = intent_router.route("Write documentary interview questions")
    assert result.assistant == "production"


def test_manual_override() -> None:
    result = intent_router.route("Anything", override="coder")
    assert result.assistant == "coder"
    assert result.confidence == 1.0
