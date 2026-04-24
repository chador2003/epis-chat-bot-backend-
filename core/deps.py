import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain_qdrant import FastEmbedSparse

from config import settings
from core.llm import get_llm
from core.embedding import get_ollama_embedding_model
from core.database import get_qdrant_client, get_async_qdrant_client, init_collection, get_vector_store

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing EPIS Chat API services...")

    try:
        app.state.llm = get_llm()
        app.state.ollama_embedding = get_ollama_embedding_model()
        app.state.sparse_embedding = FastEmbedSparse(model_name="Qdrant/bm25")
        logger.info("✅ Models initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize models: {e}")
        sys.exit(1)

    try:
        # Use sync client for collection initialization
        sync_client = get_qdrant_client()
        init_collection(sync_client)
        
        # Use async client for the vector store and app state
        async_client = get_async_qdrant_client()
        
        app.state.vector_store = get_vector_store(
            sync_client, 
            app.state.ollama_embedding, 
            app.state.sparse_embedding
        )
        app.state.qdrant_client = async_client
        logger.info("✅ Qdrant Vector Store initialized (Hybrid Sync/Async).")

    except Exception as e:
        logger.error(f"❌ CRITICAL: Qdrant setup failed: {e}")
        sys.exit(1)

    yield
    # Cleanup
    await app.state.qdrant_client.close()
    logger.info("Shutting down EPIS Chat API...")
