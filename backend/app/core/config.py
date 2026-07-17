from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "CTV-AI Core"
    app_version: str = "1.4.2"
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
    ollama_num_predict: int = 768
    ollama_think: bool = False
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
