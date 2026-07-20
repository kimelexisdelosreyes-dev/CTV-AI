import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.developer import (
    DeveloperModeStatus,
    DeveloperModeUpdate,
    DeveloperModelsPublic,
    ModelBenchmarkRequest,
    ModelBenchmarkResponsePublic,
    ModelBenchmarkResultPublic,
    PerformanceEventPublic,
    PerformanceSummaryPublic,
)
from app.services.embedding_service import EmbeddingServiceError
from app.services.knowledge_service import answer_with_knowledge
from app.services.model_router import configured_default_model
from app.services.ollama_service import OllamaServiceError, ollama_service
from app.services.performance_event_store import performance_event_store
from app.services.performance_instrumentation import AskPerformanceInstrumentation

router = APIRouter(prefix="/developer", tags=["developer"])
benchmark_lock = asyncio.Lock()

BENCHMARK_CASES = [
    ("operations_priorities", "What should the company prioritize today?"),
    ("leave_policy", "What is our leave policy?"),
    ("sony_fx3_firmware", "How do I update the Sony FX3 firmware?"),
]

WARMUP_MESSAGES = [{"role": "user", "content": "Hi"}]


def require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )


def require_developer_mode() -> None:
    if not performance_event_store.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer mode is disabled.",
        )


@router.get("/status", response_model=DeveloperModeStatus)
async def developer_status(
    current_user: User = Depends(get_current_user),
) -> DeveloperModeStatus:
    require_admin(current_user)
    return DeveloperModeStatus(enabled=performance_event_store.is_enabled())


@router.put("/status", response_model=DeveloperModeStatus)
async def update_developer_status(
    payload: DeveloperModeUpdate,
    current_user: User = Depends(get_current_user),
) -> DeveloperModeStatus:
    require_admin(current_user)
    return DeveloperModeStatus(
        enabled=performance_event_store.set_enabled(payload.enabled)
    )


@router.get(
    "/performance/recent",
    response_model=list[PerformanceEventPublic],
)
async def recent_performance_events(
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    require_admin(current_user)
    require_developer_mode()
    return performance_event_store.recent()


@router.get(
    "/performance/summary",
    response_model=PerformanceSummaryPublic,
)
async def performance_summary(
    current_user: User = Depends(get_current_user),
) -> dict:
    require_admin(current_user)
    require_developer_mode()
    return performance_event_store.summary()


@router.delete(
    "/performance/recent",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_performance_events(
    current_user: User = Depends(get_current_user),
) -> Response:
    require_admin(current_user)
    require_developer_mode()
    performance_event_store.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/models", response_model=DeveloperModelsPublic)
async def developer_models(
    current_user: User = Depends(get_current_user),
) -> DeveloperModelsPublic:
    require_admin(current_user)
    require_developer_mode()
    models = sorted(await ollama_service.list_models())
    return DeveloperModelsPublic(
        default_model=configured_default_model(),
        available_models=models,
    )


@router.post(
    "/models/benchmark",
    response_model=ModelBenchmarkResponsePublic,
)
async def benchmark_models(
    payload: ModelBenchmarkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModelBenchmarkResponsePublic:
    require_admin(current_user)
    require_developer_mode()

    if benchmark_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A model benchmark is already running.",
        )

    available_models = await ollama_service.list_models()
    comparison_model = payload.comparison_model.strip()
    default_model = configured_default_model()

    if comparison_model == default_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a comparison model that is not the current default model.",
        )

    if comparison_model not in available_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison model is not installed or available.",
        )

    async with benchmark_lock:
        results = await run_model_benchmark(
            default_model=default_model,
            comparison_model=comparison_model,
            current_user=current_user,
            db=db,
        )

    return ModelBenchmarkResponsePublic(
        default_model=default_model,
        comparison_model=comparison_model,
        results=results,
    )


async def run_model_benchmark(
    default_model: str,
    comparison_model: str,
    current_user: User,
    db: AsyncSession,
    warmup: Callable[[str], Awaitable[None]] | None = None,
) -> list[ModelBenchmarkResultPublic]:
    warmup_model = warmup or _warmup_model
    results: list[ModelBenchmarkResultPublic] = []

    for model_name in (default_model, comparison_model):
        try:
            await warmup_model(model_name)
        except (OllamaServiceError, EmbeddingServiceError):
            results.extend(
                warmup_error_results(
                    model_name=model_name,
                    error_category="ai_request_error",
                )
            )
            continue
        except Exception:
            results.extend(
                warmup_error_results(
                    model_name=model_name,
                    error_category="benchmark_warmup_error",
                )
            )
            continue

        for case_label, question in BENCHMARK_CASES:
            results.append(
                await run_benchmark_case(
                    model_name=model_name,
                    case_label=case_label,
                    question=question,
                    current_user=current_user,
                    db=db,
                )
            )

    return results


async def _warmup_model(model_name: str) -> None:
    await ollama_service.chat(WARMUP_MESSAGES, model=model_name)


def warmup_error_results(
    model_name: str,
    error_category: str,
) -> list[ModelBenchmarkResultPublic]:
    return [
        ModelBenchmarkResultPublic(
            model_name=model_name,
            case_label=case_label,
            outcome="error",
            total_request_ms=0.0,
            ollama_request_ms=0.0,
            estimated_input_tokens=0,
            estimated_output_tokens=0,
            tokens_per_second=None,
            answer_character_count=0,
            routed_intent=None,
            skipped_no_evidence=False,
            error_category=error_category,
        )
        for case_label, _ in BENCHMARK_CASES
    ]


async def run_benchmark_case(
    model_name: str,
    case_label: str,
    question: str,
    current_user: User,
    db: AsyncSession,
) -> ModelBenchmarkResultPublic:
    instrumentation = AskPerformanceInstrumentation()

    try:
        with instrumentation.measure("total_endpoint_ms"):
            await answer_with_knowledge(
                question=question,
                top_k=settings.knowledge_top_k,
                category=None,
                assistant="general",
                use_employee_context=True,
                current_user=current_user,
                db=db,
                instrumentation=instrumentation,
                model_override=model_name,
            )
    except (OllamaServiceError, EmbeddingServiceError):
        return benchmark_result_from_instrumentation(
            model_name=model_name,
            case_label=case_label,
            instrumentation=instrumentation,
            outcome="error",
            error_category="ai_request_error",
        )
    except Exception:
        return benchmark_result_from_instrumentation(
            model_name=model_name,
            case_label=case_label,
            instrumentation=instrumentation,
            outcome="error",
            error_category="benchmark_case_error",
        )

    skipped_no_evidence = instrumentation.durations_ms.get("ollama_request_ms", 0.0) <= 0

    return benchmark_result_from_instrumentation(
        model_name=model_name,
        case_label=case_label,
        instrumentation=instrumentation,
        outcome="skipped_no_evidence" if skipped_no_evidence else "success",
        error_category=None,
    )


def benchmark_result_from_instrumentation(
    model_name: str,
    case_label: str,
    instrumentation: AskPerformanceInstrumentation,
    outcome: str,
    error_category: str | None,
) -> ModelBenchmarkResultPublic:
    skipped_no_evidence = outcome == "skipped_no_evidence"

    return ModelBenchmarkResultPublic(
        model_name=model_name,
        case_label=case_label,
        outcome=outcome,
        total_request_ms=round(
            instrumentation.durations_ms.get("total_endpoint_ms", 0.0),
            3,
        ),
        ollama_request_ms=round(
            instrumentation.durations_ms.get("ollama_request_ms", 0.0),
            3,
        ),
        estimated_input_tokens=instrumentation.estimated_input_token_count,
        estimated_output_tokens=instrumentation.estimated_output_token_count,
        tokens_per_second=instrumentation.tokens_per_second(),
        answer_character_count=instrumentation.answer_character_count,
        routed_intent=instrumentation.routed_intent,
        skipped_no_evidence=skipped_no_evidence,
        error_category=error_category,
    )
