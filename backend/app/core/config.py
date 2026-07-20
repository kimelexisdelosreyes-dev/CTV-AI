from functools import lru_cache
from typing import ClassVar, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.version import APP_VERSION

class Settings(BaseSettings):
    app_name: str = "CTV-AI Core"
    app_version: ClassVar[str] = APP_VERSION
    api_v1_prefix: str = "/api/v1"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    ollama_general_model: str = "qwen3:14b"
    ollama_production_model: str = "qwen3:14b"
    ollama_graphics_model: str = "qwen3:14b"
    ollama_drone_model: str = "qwen3:14b"
    ollama_it_model: str = "qwen3:14b"
    ollama_coder_model: str = "qwen3:14b"
    ollama_light_model: str = "qwen3:14b"
    ollama_comedy_model: str = "qwen3:14b"
    ollama_embedding_model: str = "embeddinggemma"
    ollama_num_predict: int = 768
    ollama_think: bool = False
    ctv_one_model_router_enabled: bool = True
    ctv_one_model_fast: str | None = "qwen3:8b"
    ctv_one_model_balanced: str | None = "qwen3:8b"
    ctv_one_model_reasoning: str | None = "deepseek-r1:14b"
    ctv_one_model_operations: str | None = "qwen3:8b"
    ctv_one_model_knowledge: str | None = "qwen3:8b"
    ctv_one_model_default: str | None = "qwen3:8b"
    ctv_one_model_availability_ttl_seconds: float = 300.0
    company_brain_max_knowledge_chunks: int = 4
    company_brain_max_knowledge_chars: int = 3200
    company_brain_max_operational_tasks: int = 6
    company_brain_max_operational_chars: int = 2200
    company_brain_max_employee_chars: int = 900
    company_brain_max_history_messages: int = 4
    company_brain_max_history_chars: int = 1200
    company_brain_max_total_prompt_chars: int = 5200
    company_brain_knowledge_timeout_seconds: float = 30.0
    company_brain_operations_timeout_seconds: float = 30.0
    company_brain_employee_timeout_seconds: float = 10.0
    company_brain_history_timeout_seconds: float = 5.0
    operations_sync_enabled: bool = True
    operations_sync_interval_seconds: float = 300.0
    operations_snapshot_max_age_seconds: float = 300.0
    operations_sync_timeout_seconds: float = 60.0
    ctv_one_operations_snapshot_fresh_seconds: float = 900.0
    ctv_one_operations_snapshot_aging_seconds: float = 3600.0
    ctv_one_operations_snapshot_stale_seconds: float = 21600.0
    ctv_one_monday_snapshot_refresh_enabled: bool = True
    ctv_one_monday_snapshot_refresh_interval_seconds: float = 900.0
    ctv_one_monday_snapshot_refresh_on_startup: bool = False
    ctv_one_monday_snapshot_retry_attempts: int = 3
    ctv_one_monday_snapshot_retry_base_seconds: float = 0.5

    ctv_ai_api_key: str = "ctv-ai-local"
    database_url: str = "postgresql+asyncpg://ctvai:ctvai_change_me@127.0.0.1:5432/ctvai"
    qdrant_url: str = "http://127.0.0.1:6333"

    knowledge_collection: str = "ctv_company_knowledge"
    knowledge_upload_dir: str = r"B:\CTV_AI\company_data\ingested"
    knowledge_max_file_mb: int = 200
    knowledge_max_pages: int = 300
    knowledge_chunk_size: int = 900
    knowledge_chunk_overlap: int = 150
    knowledge_top_k: int = 5
    knowledge_embed_batch_size: int = 16
    knowledge_qdrant_batch_size: int = 64
    knowledge_min_text_chars_per_page: int = 40

    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ocr_languages: str = "eng+chi_sim+chi_tra"
    ocr_dpi: int = 200

    jwt_secret_key: str = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    log_level: str = "INFO"
    request_timeout_seconds: float = 300.0
    embedding_validation_timeout_seconds: float = 10.0
    performance_log_path: str = r"B:\CTV_AI\logs\performance.jsonl"
    performance_log_max_bytes: int = 5_000_000
    performance_log_backup_count: int = 5
    ctv_one_semantic_cache_enabled: bool = True
    ctv_one_semantic_cache_exact_enabled: bool = True
    ctv_one_semantic_cache_similarity_enabled: bool = True
    ctv_one_semantic_cache_similarity_threshold: float = 0.94
    ctv_one_semantic_cache_default_ttl_seconds: int = 86400
    ctv_one_semantic_cache_operations_ttl_seconds: int = 900
    ctv_one_semantic_cache_max_answer_chars: int = 12000
    ctv_one_semantic_cache_max_candidates: int = 5
    ctv_one_semantic_cache_prompt_policy_version: str = "p2.5-v1"
    ctv_one_semantic_cache_router_policy_version: str = "p2.4.1-v1"
    ctv_one_inference_queue_enabled: bool = True
    ctv_one_inference_global_concurrency: int = 2
    ctv_one_inference_global_queue_size: int = 20
    ctv_one_inference_default_timeout_seconds: float = 180.0
    ctv_one_inference_queue_wait_timeout_seconds: float = 120.0
    ctv_one_inference_model_qwen3_8b_concurrency: int = 2
    ctv_one_inference_model_deepseek_r1_14b_concurrency: int = 1
    ctv_one_inference_per_user_active_limit: int = 1
    ctv_one_inference_per_user_queue_limit: int = 3
    ctv_one_inference_shutdown_grace_seconds: float = 30.0
    ctv_one_inference_priority_aging_seconds: float = 30.0
    ctv_one_supervisor_enabled: bool = True
    ctv_one_supervisor_default_mode: Literal["auto", "direct", "supervised"] = "auto"
    ctv_one_supervisor_llm_planning_enabled: bool = True
    ctv_one_supervisor_max_tasks: int = 6
    ctv_one_supervisor_max_depth: int = 3
    ctv_one_supervisor_max_parallel_tasks: int = 3
    ctv_one_supervisor_planner_timeout_seconds: float = 20.0
    ctv_one_supervisor_task_timeout_seconds: float = 60.0
    ctv_one_supervisor_total_timeout_seconds: float = 180.0
    ctv_one_supervisor_fallback_direct: bool = True
    ctv_one_supervisor_cache_enabled: bool = False
    ctv_one_supervisor_stream_events_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
