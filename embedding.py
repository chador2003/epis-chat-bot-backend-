from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models

from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from config import settings
from langchain_ollama import OllamaEmbeddings

# def get_embedding_model():
#     model_name = settings.EMBEDDING_MODEL
#     model_kwargs = {"device": "cpu"}  
#     encode_kwargs = {"normalize_embeddings": True} 
#     return HuggingFaceBgeEmbeddings(
#         model_name=model_name,
#         model_kwargs=model_kwargs,
#         encode_kwargs=encode_kwargs
#     )

def get_ollama_embedding_model():
    # Remove the trailing comma and move parameters inside the constructor
    embeddings = OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL
    )
    return embeddings