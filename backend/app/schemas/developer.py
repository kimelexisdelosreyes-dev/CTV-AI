from pydantic import BaseModel, Field


class DeveloperModeStatus(BaseModel):
    enabled: bool


class DeveloperModeUpdate(BaseModel):
    enabled: bool


class RoutedCollectionSearchMetric(BaseModel):
    collection: str | None = None
    duration_ms: float | None = None
    retrieved_chunk_count: int | None = None


class PerformanceEventPublic(BaseModel):
    timestamp: str | None = None
    outcome: str | None = None
    routed_intent: str | None = None
    routing_confidence: float | None = None
    total_endpoint_ms: float | None = None
    intelligence_router_ms: float | None = None
    employee_context_ms: float | None = None
    monday_operational_context_ms: float | None = None
    embedding_ms: float | None = None
    qdrant_vector_search_ms: float | None = None
    prompt_assembly_ms: float | None = None
    ollama_request_ms: float | None = None
    prompt_character_count: int | None = None
    prompt_size: int | None = None
    estimated_input_token_count: int | None = None
    estimated_output_token_count: int | None = None
    tokens_per_second: float | None = None
    answer_character_count: int | None = None
    collection_count: int | None = None
    retrieved_chunk_count: int | None = None
    operational_task_count: int | None = None
    routed_collection_searches: list[RoutedCollectionSearchMetric] = Field(
        default_factory=list
    )
    model_name: str | None = None
    gpu_utilization: float | None = None
    cpu_utilization: float | None = None


class PerformanceSummaryPublic(BaseModel):
    request_count: int
    success_count: int
    failure_count: int
    average_total_duration_ms: float
    median_total_duration_ms: float
    p95_total_duration_ms: float
    average_ollama_duration_ms: float
    average_monday_duration_ms: float
    average_employee_context_duration_ms: float
    average_embedding_duration_ms: float
    average_qdrant_duration_ms: float
    average_estimated_input_tokens: float
    average_tokens_per_second: float
    slowest_stage: str | None
    counts_by_routed_intent: dict[str, int]


class DeveloperModelsPublic(BaseModel):
    default_model: str
    available_models: list[str]


class ModelBenchmarkRequest(BaseModel):
    comparison_model: str


class ModelBenchmarkResultPublic(BaseModel):
    model_name: str
    case_label: str
    outcome: str
    total_request_ms: float
    ollama_request_ms: float
    estimated_input_tokens: int
    estimated_output_tokens: int
    tokens_per_second: float | None
    answer_character_count: int
    routed_intent: str | None
    skipped_no_evidence: bool
    error_category: str | None = None


class ModelBenchmarkResponsePublic(BaseModel):
    default_model: str
    comparison_model: str
    results: list[ModelBenchmarkResultPublic]
