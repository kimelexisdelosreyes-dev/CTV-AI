from functools import lru_cache
from typing import ClassVar, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.version import APP_VERSION

class Settings(BaseSettings):
    app_name: str = "CTV-AI Core"
    app_version: ClassVar[str] = APP_VERSION
    api_v1_prefix: str = "/api/v1"
    cors_allowed_origins: str = (
        "http://127.0.0.1:3001,"
        "http://localhost:3001"
    )

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
    ctv_one_ai_runtime_enabled: bool = False
    ctv_one_prompt_enterprise_context_enabled: bool = False
    ctv_one_enterprise_intelligence_enabled: bool = False
    ctv_one_enterprise_policy_engine_enabled: bool = False
    ctv_one_capability_execution_enabled: bool = False
    ctv_one_capability_governance_enabled: bool = False
    ctv_one_capability_framework_enabled: bool = False
    ctv_one_capability_api_enabled: bool = False
    ctv_one_prompt_company_brain_enabled: bool = False
    ctv_one_prompt_knowledge_context_enabled: bool = False
    ctv_one_prompt_enterprise_max_chars: int = 4000
    ctv_one_prompt_company_brain_max_chars: int = 2000
    ctv_one_prompt_knowledge_max_chars: int = 2000
    ctv_one_prompt_enterprise_max_items: int = 4
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
    ctv_one_agent_runtime_enabled: bool = True
    ctv_one_agent_health_poll_enabled: bool = True
    ctv_one_agent_health_poll_seconds: float = 60.0
    ctv_one_agent_health_timeout_seconds: float = 5.0
    ctv_one_agent_initialize_timeout_seconds: float = 30.0
    ctv_one_agent_shutdown_timeout_seconds: float = 15.0
    ctv_one_agent_failure_threshold: int = 3
    ctv_one_agent_recovery_success_threshold: int = 2
    ctv_one_agent_knowledge_enabled: bool = True
    ctv_one_agent_operations_enabled: bool = True
    ctv_one_agent_employee_enabled: bool = True
    ctv_one_agent_reasoning_enabled: bool = True
    ctv_one_agent_composer_enabled: bool = True
    ctv_one_agent_disabled_capabilities: str = ""
    ctv_one_agent_default_max_inference_calls: int = 1
    ctv_one_agent_default_max_retrieval_calls: int = 3
    ctv_one_agent_default_max_evidence_items: int = 12
    ctv_one_agent_default_max_output_chars: int = 16000
    ctv_one_agent_default_max_queue_wait_seconds: float = 120.0
    ctv_one_agent_reasoning_timeout_seconds: float = 90.0
    ctv_one_agent_composer_timeout_seconds: float = 120.0
    ctv_one_agent_composition_max_evidence_items: int = 8
    ctv_one_agent_composition_max_chars_per_result: int = 2500
    ctv_one_agent_composition_max_total_chars: int = 8000
    ctv_one_semantic_cache_hot_exact_max_entries: int = 128
    ctv_one_atlas_enabled: bool = True
    ctv_one_atlas_runtime_version: str = "1.0.0"
    ctv_one_atlas_provider_contract_version: str = "1.0"
    ctv_one_atlas_context_package_version: str = "1.0"
    ctv_one_atlas_health_poll_enabled: bool = True
    ctv_one_atlas_health_poll_seconds: float = 60.0
    ctv_one_atlas_health_timeout_seconds: float = 5.0
    ctv_one_atlas_initialize_timeout_seconds: float = 30.0
    ctv_one_atlas_shutdown_timeout_seconds: float = 15.0
    ctv_one_atlas_failure_threshold: int = 3
    ctv_one_atlas_recovery_threshold: int = 2
    ctv_one_forge_atlas_enabled: bool = False
    ctv_one_forge_atlas_max_tokens: int = 4000
    ctv_one_atlas_shadow_enabled: bool = False
    ctv_one_atlas_canary_enabled: bool = False
    ctv_one_atlas_live_enabled: bool = False
    ctv_one_atlas_canary_percentage: int = 0
    ctv_one_atlas_canary_users: str = ""
    ctv_one_atlas_canary_emergency_disabled: bool = False
    ctv_one_nexus_provider_enabled: bool = True
    ctv_one_nexus_max_entities: int = 16
    ctv_one_nexus_max_relationships: int = 32
    ctv_one_nexus_max_traversal_depth: int = 2
    ctv_one_nexus_max_execution_seconds: float = 1.0
    ctv_one_nexus_max_import_batches: int = 16
    ctv_one_nexus_max_metadata_bytes: int = 4096
    ctv_one_nexus_max_entity_aliases: int = 8
    ctv_one_nexus_max_relationships_per_entity: int = 64
    ctv_one_nexus_max_snapshot_bytes: int = 1_000_000
    ctv_one_nexus_max_build_seconds: float = 5.0
    ctv_one_nexus_ingestion_enabled: bool = False
    ctv_one_nexus_company_brain_connector_enabled: bool = False
    ctv_one_nexus_archive_connector_enabled: bool = False
    ctv_one_nexus_max_connectors_per_run: int = 4
    ctv_one_nexus_max_records_per_connector: int = 1_000
    ctv_one_nexus_connector_timeout_seconds: float = 5.0
    ctv_one_nexus_import_history_capacity: int = 100
    ctv_one_nexus_previous_snapshot_retained: bool = True
    ctv_one_nexus_incremental_enabled: bool = False
    ctv_one_nexus_validate_only_default: bool = True
    ctv_one_knowledge_evolution_enabled: bool = False
    ctv_one_knowledge_evolution_event_capacity: int = 10_000
    ctv_one_knowledge_evolution_recommendation_capacity: int = 1_000
    ctv_one_knowledge_evolution_minimum_sample_size: int = 10
    ctv_one_knowledge_evolution_stale_days_default: int = 90
    ctv_one_knowledge_evolution_connector_failure_threshold: float = 0.2
    ctv_one_knowledge_evolution_empty_retrieval_threshold: float = 0.2
    ctv_one_knowledge_evolution_fallback_threshold: float = 0.1
    ctv_one_knowledge_evolution_budget_pressure_threshold: float = 80.0
    ctv_one_knowledge_evolution_unused_entity_threshold: float = 0.8
    ctv_one_knowledge_evolution_recommendation_suppression_hours: int = 24

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
