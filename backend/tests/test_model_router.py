import pytest

from app.core.config import Settings, settings
from app.services.model_router import ModelRouter, ModelRoutingInput
from app.services import model_router as router_module
from app.services.ollama_service import OllamaServiceError
from app.services.performance_instrumentation import AskPerformanceInstrumentation


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def routing_input(**overrides) -> ModelRoutingInput:
    values = {
        "question": "What policy applies?",
        "intent": "policy",
        "include_knowledge": True,
        "include_operations": False,
        "include_employee": False,
        "source_count": 1,
        "operations_task_count": 0,
        "final_prompt_chars": 800,
        "estimated_prompt_tokens": 200,
        "streaming": False,
    }
    values.update(overrides)
    return ModelRoutingInput(**values)


def configure_models(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_model_router_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_model_fast", "fast:latest")
    monkeypatch.setattr(settings, "ctv_one_model_balanced", "balanced:latest")
    monkeypatch.setattr(settings, "ctv_one_model_reasoning", "reasoning:latest")
    monkeypatch.setattr(settings, "ctv_one_model_operations", "operations:latest")
    monkeypatch.setattr(settings, "ctv_one_model_knowledge", "knowledge:latest")
    monkeypatch.setattr(settings, "ctv_one_model_default", "default:latest")


def install_models(monkeypatch, models=None) -> None:
    async def list_models():
        return set(
            models
            or {
                "fast:latest",
                "balanced:latest",
                "reasoning:latest",
                "operations:latest",
                "knowledge:latest",
                "default:latest",
            }
        )

    monkeypatch.setattr(router_module.ollama_service, "list_models", list_models)


@pytest.mark.anyio
async def test_router_disabled_uses_existing_ollama_model(monkeypatch) -> None:
    router = ModelRouter()
    monkeypatch.setattr(settings, "ctv_one_model_router_enabled", False)
    monkeypatch.setattr(settings, "ollama_model", "existing:latest")

    decision = await router.route(routing_input())

    assert decision.selected_model == "existing:latest"
    assert decision.fallback_reason == "router_disabled"
    assert decision.availability_checked is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("overrides", "expected_role"),
    [
        (
            {
                "question": "What tasks are due?",
                "intent": "operations",
                "include_knowledge": False,
                "include_operations": True,
            },
            "operations",
        ),
        (
            {
                "question": "Combine tasks with policy",
                "intent": "mixed",
                "include_operations": True,
            },
            "balanced",
        ),
    ],
)
async def test_default_local_policy_uses_qwen_8b(
    monkeypatch,
    overrides,
    expected_role,
) -> None:
    defaults = Settings(_env_file=None)
    for field in (
        "ctv_one_model_router_enabled",
        "ctv_one_model_fast",
        "ctv_one_model_balanced",
        "ctv_one_model_reasoning",
        "ctv_one_model_operations",
        "ctv_one_model_knowledge",
        "ctv_one_model_default",
        "ollama_model",
    ):
        monkeypatch.setattr(settings, field, getattr(defaults, field))
    install_models(monkeypatch, {"qwen3:8b", "deepseek-r1:14b"})

    decision = await ModelRouter().route(routing_input(**overrides))

    expected_model = {
        "operations": defaults.ctv_one_model_operations,
        "balanced": defaults.ctv_one_model_balanced,
    }[expected_role]
    assert decision.selected_model == expected_model
    assert decision.model_role == expected_role


@pytest.mark.anyio
@pytest.mark.parametrize(
    "question",
    [
        "Analyze the situation",
        "Recommend an approach",
        "Create a strategy",
        "Assess the risk",
        "Forecast next quarter",
        "Explain the tradeoffs",
        "Compare options for the rollout",
        "Create a long-term plan",
        "Make a decision",
        "List the pros and cons",
    ],
)
async def test_explicit_complex_phrases_select_reasoning(
    monkeypatch,
    question,
) -> None:
    defaults = Settings(_env_file=None)
    monkeypatch.setattr(settings, "ctv_one_model_router_enabled", True)
    monkeypatch.setattr(
        settings,
        "ctv_one_model_reasoning",
        defaults.ctv_one_model_reasoning,
    )
    monkeypatch.setattr(
        settings, "ctv_one_model_default", defaults.ctv_one_model_default
    )
    install_models(
        monkeypatch,
        {defaults.ctv_one_model_default, defaults.ctv_one_model_reasoning},
    )

    decision = await ModelRouter().route(
        routing_input(
            question=question,
            intent="general",
            include_knowledge=False,
        )
    )

    assert decision.selected_model == defaults.ctv_one_model_reasoning
    assert decision.model_role == "reasoning"


@pytest.mark.anyio
async def test_prompt_length_alone_does_not_select_reasoning(monkeypatch) -> None:
    configure_models(monkeypatch)
    install_models(monkeypatch)

    decision = await ModelRouter().route(
        routing_input(
            question="Provide the requested information",
            intent="general",
            include_knowledge=False,
            final_prompt_chars=8_000,
            estimated_prompt_tokens=2_000,
        )
    )

    assert decision.selected_model == settings.ctv_one_model_default
    assert decision.model_role == "fallback"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("input_overrides", "expected_model", "expected_role"),
    [
        ({}, "knowledge:latest", "knowledge"),
        (
            {
                "question": "What tasks are due?",
                "intent": "operations",
                "include_knowledge": False,
                "include_operations": True,
                "operations_task_count": 3,
            },
            "operations:latest",
            "operations",
        ),
        (
            {
                "question": "What is my role?",
                "intent": "employee",
                "include_knowledge": False,
                "include_employee": True,
            },
            "fast:latest",
            "fast",
        ),
        (
            {
                "question": "Compare tasks with policy",
                "intent": "mixed",
                "include_operations": True,
            },
            "balanced:latest",
            "balanced",
        ),
        (
            {
                "question": "Combine tasks with policy",
                "intent": "mixed",
                "include_operations": True,
                "final_prompt_chars": 4_500,
                "estimated_prompt_tokens": 1_125,
            },
            "balanced:latest",
            "balanced",
        ),
        (
            {
                "question": "Analyze the strategic risks and recommend tradeoffs",
                "intent": "general",
                "include_knowledge": False,
            },
            "reasoning:latest",
            "reasoning",
        ),
    ],
)
async def test_router_selects_model_by_context_and_complexity(
    monkeypatch,
    input_overrides,
    expected_model,
    expected_role,
) -> None:
    configure_models(monkeypatch)
    install_models(monkeypatch)

    decision = await ModelRouter().route(routing_input(**input_overrides))

    assert decision.selected_model == expected_model
    assert decision.model_role == expected_role
    assert decision.fallback_used is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("overrides", "setting_name", "expected_role"),
    [
        ({}, "ctv_one_model_knowledge", "knowledge"),
        (
            {
                "question": "What tasks are due?",
                "intent": "operations",
                "include_knowledge": False,
                "include_operations": True,
            },
            "ctv_one_model_operations",
            "operations",
        ),
        (
            {
                "question": "What should I focus on?",
                "intent": "employee",
                "include_knowledge": False,
                "include_employee": True,
            },
            "ctv_one_model_fast",
            "fast",
        ),
        (
            {
                "question": "Combine tasks with policy",
                "intent": "mixed",
                "include_operations": True,
            },
            "ctv_one_model_balanced",
            "balanced",
        ),
        (
            {
                "question": "Analyze the strategic risks",
                "intent": "general",
                "include_knowledge": False,
            },
            "ctv_one_model_reasoning",
            "reasoning",
        ),
        (
            {
                "question": "Hello",
                "intent": "general",
                "include_knowledge": False,
            },
            "ctv_one_model_default",
            "fallback",
        ),
    ],
)
async def test_each_router_role_uses_its_configured_setting(
    monkeypatch,
    overrides,
    setting_name,
    expected_role,
) -> None:
    configure_models(monkeypatch)
    install_models(monkeypatch)

    decision = await ModelRouter().route(routing_input(**overrides))

    assert decision.selected_model == getattr(settings, setting_name)
    assert decision.model_role == expected_role


@pytest.mark.anyio
async def test_unavailable_role_model_falls_back_to_default(monkeypatch) -> None:
    configure_models(monkeypatch)
    install_models(monkeypatch, {"default:latest"})

    decision = await ModelRouter().route(routing_input())

    assert decision.selected_model == "default:latest"
    assert decision.model_role == "fallback"
    assert decision.fallback_reason == "model_unavailable"


@pytest.mark.anyio
async def test_unconfigured_role_model_falls_back_safely(monkeypatch) -> None:
    configure_models(monkeypatch)
    monkeypatch.setattr(settings, "ctv_one_model_knowledge", None)
    install_models(monkeypatch, {"default:latest"})

    decision = await ModelRouter().route(routing_input())

    assert decision.selected_model == "default:latest"
    assert decision.fallback_reason == "model_not_configured"


@pytest.mark.anyio
async def test_explicit_model_is_preserved_without_availability_call(monkeypatch) -> None:
    configure_models(monkeypatch)

    async def unexpected_list():
        raise AssertionError("explicit model should not list models")

    monkeypatch.setattr(router_module.ollama_service, "list_models", unexpected_list)

    decision = await ModelRouter().route(
        routing_input(explicit_model="qwen3:14b")
    )

    assert decision.selected_model == "qwen3:14b"
    assert decision.model_role == "explicit"
    assert decision.fallback_used is False


@pytest.mark.anyio
async def test_availability_is_cached(monkeypatch) -> None:
    configure_models(monkeypatch)
    calls = 0

    async def list_models():
        nonlocal calls
        calls += 1
        return {"knowledge:latest", "default:latest"}

    monkeypatch.setattr(router_module.ollama_service, "list_models", list_models)
    router = ModelRouter()

    first = await router.route(routing_input())
    second = await router.route(routing_input())

    assert calls == 1
    assert first.availability_checked is True
    assert second.availability_checked is False


@pytest.mark.anyio
async def test_availability_failure_does_not_fail_routing(monkeypatch) -> None:
    configure_models(monkeypatch)

    async def unavailable():
        raise OllamaServiceError()

    monkeypatch.setattr(router_module.ollama_service, "list_models", unavailable)

    decision = await ModelRouter().route(routing_input())

    assert decision.selected_model == "knowledge:latest"
    assert decision.availability_checked is True
    assert decision.fallback_used is False


@pytest.mark.anyio
async def test_unknown_route_uses_explainable_default_fallback(monkeypatch) -> None:
    configure_models(monkeypatch)
    install_models(monkeypatch)

    decision = await ModelRouter().route(
        routing_input(
            question="Hello",
            intent="general",
            include_knowledge=False,
        )
    )

    assert decision.selected_model == "default:latest"
    assert decision.fallback_reason == "unsupported_route"


@pytest.mark.anyio
async def test_routing_metrics_contain_no_request_content(monkeypatch) -> None:
    configure_models(monkeypatch)
    install_models(monkeypatch)
    secret_question = "private employee context must not be logged"
    decision = await ModelRouter().route(routing_input(question=secret_question))
    instrumentation = AskPerformanceInstrumentation()

    instrumentation.record_model_routing(decision)
    report = instrumentation.to_report()

    assert report["metrics"]["model_selected"] == "knowledge:latest"
    assert secret_question not in str(report)
