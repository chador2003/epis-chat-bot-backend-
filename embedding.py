from langchain_ollama import OllamaEmbeddings
from config import settings

def get_ollama_embedding_model():
    """
    Initialize and return the Ollama embedding model based on configuration.
    """
    return OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL
    )
