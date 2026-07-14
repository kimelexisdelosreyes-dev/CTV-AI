from app.services.intelligence_router import intelligence_router


def test_operations_route() -> None:
    route = intelligence_router.route(
        "What should the company prioritize today?"
    )
    assert route.intent == "operations"
    assert route.use_operations is True
    assert route.collections == []


def test_policy_route() -> None:
    route = intelligence_router.route("What is our leave policy?")
    assert route.intent == "policy"
    assert route.use_operations is False
    assert "company-policies" in route.collections
    assert "hr-policies" in route.collections


def test_equipment_route() -> None:
    route = intelligence_router.route(
        "How do I update the Sony FX3 firmware?"
    )
    assert route.intent in {"equipment", "mixed"}
    assert "equipment-manuals" in route.collections
