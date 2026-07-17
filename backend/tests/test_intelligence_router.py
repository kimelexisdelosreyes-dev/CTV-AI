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


def test_plural_and_variant_router_terms() -> None:
    assert intelligence_router.route("What are our priorities?").intent == "operations"
    assert intelligence_router.route("Which policies apply?").intent == "policy"
    assert intelligence_router.route("Open the equipment manuals.").intent == "equipment"
    assert intelligence_router.route("Where are production SOPs?").intent == "production"
    assert intelligence_router.route("Use the brand guidelines.").intent == "branding"
    assert intelligence_router.route("Technical issue troubleshooting").intent == "technical"
    assert intelligence_router.route("Find project references.").intent == "branding"


def test_all_baseline_prompts_route_to_intended_capability() -> None:
    cases = {
        "operations_priorities": (
            "What are the highest operational priorities for the company today?",
            "operations",
            True,
        ),
        "overdue_tasks": (
            "Which tasks are overdue, and what should be handled first?",
            "operations",
            True,
        ),
        "company_policy": (
            "What company policy should I follow for time off or leave requests?",
            "policy",
            False,
        ),
        "equipment_manual": (
            "What setup steps should I follow from the approved equipment manuals?",
            "equipment",
            False,
        ),
        "production_sop": (
            "Summarize the approved production SOP for preparing a shoot.",
            "production",
            False,
        ),
        "technical_troubleshooting": (
            "How should I troubleshoot a technical issue with production equipment?",
            "technical",
            False,
        ),
        "brand_guidance": (
            "What brand guidance should I follow when preparing client-facing material?",
            "branding",
            False,
        ),
        "mixed_operations_plus_knowledge": (
            "Combine current operations priorities with relevant approved knowledge guidance.",
            "operations",
            True,
        ),
        "employee_context_question": (
            "Based on my role and preferences, what should I focus on next?",
            "employee",
            True,
        ),
        "repeat_operations_priorities": (
            "What are the highest operational priorities for the company today?",
            "operations",
            True,
        ),
    }

    for label, (prompt, intent, use_operations) in cases.items():
        route = intelligence_router.route(prompt)
        assert route.intent == intent, label
        assert route.use_operations is use_operations, label
