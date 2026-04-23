from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None
    MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    QDRANT_HOST: str = "http://localhost:6333"
    COLLECTION_NAME: str = "epis_faqs"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    TOP_K: int = 10
    TEMPERATURE: float = 0.0
    MAX_CONTEXT_CHARS: int = 20000
    
    # Constant for sparse vector name to avoid magic strings throughout the app
    SPARSE_VECTOR_NAME: str = "sparse-text"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
