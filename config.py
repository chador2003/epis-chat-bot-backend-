import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    MODEL = os.getenv("MODEL")
    QDRANT_HOST = os.getenv("QDRANT_HOST")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
    VLLM_BASE_URL = os.getenv("VLLM_BASE_URL")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    TOP_K = os.getenv("TOP_K")
    TEMPERATURE = os.getenv("TEMPERATURE")
    MAX_CONTEXT_CHARS = os.getenv("MAX_CONTEXT_CHARS")


settings = Settings()