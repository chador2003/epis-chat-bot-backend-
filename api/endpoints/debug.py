from fastapi import APIRouter, Request, HTTPException
from schemas.chat import ChatRequest
from config import settings
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/test-retrieval")
async def debug_retrieval(request: Request, chat_request: ChatRequest):
    """Debug endpoint to test chunk retrieval and see scores with Hybrid Search"""
    try:
        vector_store = request.app.state.vector_store
        
        retrieved_results = await vector_store.asimilarity_search_with_score(
            chat_request.query,
            k=10 
        )
        
        results = []
        for i, (doc, score) in enumerate(retrieved_results, 1):
            results.append({
                "rank": i,
                "score": float(score),
                "source": doc.metadata.get("source", "Unknown"),
                "chunk_index": doc.metadata.get("chunk_index", "N/A"),
                "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "full_content": doc.page_content
            })
        
        return {
            "query": chat_request.query,
            "retrieval_mode": "hybrid",
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/reset-collection")
async def reset_collection(request: Request):
    client = request.app.state.qdrant_client
    await client.delete_collection(settings.COLLECTION_NAME)
    await client.create_collection(
        collection_name=settings.COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        sparse_vectors_config={
            settings.SPARSE_VECTOR_NAME: SparseVectorParams()
        }
    )
    return {"message": "Collection reset. Re-ingest your PDFs with Hybrid Search support."}
