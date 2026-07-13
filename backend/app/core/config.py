from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CTV-AI Core"
    app_version: str = "1.3.0"
    api_v1_prefix: str = "/api/v1"

    ollama_base_url: str = "http://127.0.0.1:11434"

    ollama_model: str = "qwen3:14b"
    ollama_general_model: str = "qwen3:14b"
    ollama_production_model: str = "qwen3:14b"
    ollama_graphics_model: str = "qwen3:14b"
    ollama_drone_model: str = "qwen3:14b"
    ollama_it_model: str = "qwen3:14b"
    ollama_coder_model: str = "qwen3:14b"
    ollama_light_model: str = "qwen3:14b"
    ollama_comedy_model: str = "qwen3:14b"
    ollama_embedding_model: str = "embeddinggemma"

    ctv_ai_api_key: str = "ctv-ai-local"

    database_url: str = (
        "postgresql+asyncpg://ctvai:ctvai_change_me@127.0.0.1:5432/ctvai"
    )
    qdrant_url: str = "http://127.0.0.1:6333"

    knowledge_collection: str = "ctv_company_knowledge"
    knowledge_upload_dir: str = r"B:\CTV_AI\company_data\ingested"
    knowledge_max_file_mb: int = 25
    knowledge_chunk_size: int = 900
    knowledge_chunk_overlap: int = 150
    knowledge_top_k: int = 5

    jwt_secret_key: str = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    log_level: str = "INFO"
    request_timeout_seconds: float = 180.0

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