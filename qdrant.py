from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from embedding import get_ollama_embedding_model
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

def init_collection(client: QdrantClient):
    """Ensure the collection exists with correct Hybrid Search configuration."""
    collections_response = client.get_collections()
    existing_collections = [c.name for c in collections_response.collections]
    
    needs_recreate = False
    if settings.COLLECTION_NAME in existing_collections:
        collection_info = client.get_collection(settings.COLLECTION_NAME)
        if not collection_info.config.params.sparse_vectors or settings.SPARSE_VECTOR_NAME not in collection_info.config.params.sparse_vectors:
            logger.warning(f"Collection '{settings.COLLECTION_NAME}' is missing sparse vectors. Recreating...")
            client.delete_collection(settings.COLLECTION_NAME)
            needs_recreate = True
    else:
        needs_recreate = True

    if needs_recreate:
        logger.info(f"Initializing collection '{settings.COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            sparse_vectors_config={
                settings.SPARSE_VECTOR_NAME: SparseVectorParams()
            }
        )
        logger.info(f"✅ Created collection: {settings.COLLECTION_NAME}")
    else:
        logger.info(f"✅ Collection '{settings.COLLECTION_NAME}' is already correctly configured.")

def get_vector_store(client: QdrantClient, embeddings, sparse_embeddings) -> QdrantVectorStore:
    """Initialize and return the LangChain QdrantVectorStore."""
    return QdrantVectorStore(
        client=client,
        collection_name=settings.COLLECTION_NAME,
        embedding=embeddings,
        sparse_embedding=sparse_embeddings,
        sparse_vector_name=settings.SPARSE_VECTOR_NAME,
        retrieval_mode=RetrievalMode.HYBRID,
        validate_collection_config=True # Can re-enable for sync client
    )
