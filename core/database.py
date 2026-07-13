from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from core.embedding import get_ollama_embedding_model
from config import settings
import logging

logger = logging.getLogger(__name__)

def get_qdrant_client() -> QdrantClient:
    """Initialize and return the standard QdrantClient."""
    return QdrantClient(
        url=settings.QDRANT_HOST,
        timeout=30.0,
        check_compatibility=False
    )

def get_async_qdrant_client() -> AsyncQdrantClient:
    """Initialize and return the AsyncQdrantClient."""
    return AsyncQdrantClient(
        url=settings.QDRANT_HOST,
        timeout=30.0,
        check_compatibility=False
    )

def init_collection(client: QdrantClient):
    """Ensure the collection exists with correct Hybrid Search configuration.

    Never deletes an existing collection: if the config is wrong, we raise
    so ingested data is not silently destroyed.
    """
    collections_response = client.get_collections()
    existing_collections = [c.name for c in collections_response.collections]

    if settings.COLLECTION_NAME in existing_collections:
        collection_info = client.get_collection(settings.COLLECTION_NAME)
        sparse_vectors = collection_info.config.params.sparse_vectors
        if not sparse_vectors or settings.SPARSE_VECTOR_NAME not in sparse_vectors:
            raise RuntimeError(
                f"Collection '{settings.COLLECTION_NAME}' exists but is missing the "
                f"sparse vector '{settings.SPARSE_VECTOR_NAME}' required for hybrid search. "
                f"Refusing to auto-delete it. If you really want to recreate it, delete it "
                f"manually first, e.g.:\n"
                f"  curl -X DELETE {settings.QDRANT_HOST}/collections/{settings.COLLECTION_NAME}"
            )
        logger.info(f"✅ Collection '{settings.COLLECTION_NAME}' is already correctly configured.")
        return

    logger.info(f"Initializing collection '{settings.COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=settings.COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        sparse_vectors_config={
            settings.SPARSE_VECTOR_NAME: SparseVectorParams()
        }
    )
    logger.info(f"✅ Created collection: {settings.COLLECTION_NAME}")

def get_vector_store(client: QdrantClient, embeddings, sparse_embeddings) -> QdrantVectorStore:
    """Initialize and return the LangChain QdrantVectorStore."""
    return QdrantVectorStore(
        client=client,
        collection_name=settings.COLLECTION_NAME,
        embedding=embeddings,
        sparse_embedding=sparse_embeddings,
        sparse_vector_name=settings.SPARSE_VECTOR_NAME,
        retrieval_mode=RetrievalMode.HYBRID,
        validate_collection_config=True
    )