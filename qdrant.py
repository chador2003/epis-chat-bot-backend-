from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, Distance, VectorParams, SparseVectorParams
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import FastEmbedSparse
from typing import List, Dict, Any
import asyncio
from config import settings

# Configuration
COLLECTION_NAME = settings.COLLECTION_NAME
EMBEDDING_MODEL = settings.EMBEDDING_MODEL

async def get_async_qdrant_client():
    return AsyncQdrantClient(url=settings.QDRANT_HOST)

def get_embeddings():
    return OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL
    )

def get_sparse_embeddings():
    return FastEmbedSparse(model_name="Qdrant/bm25")

async def retrieve_relevant_chunks_hybrid(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chunks from Qdrant using Hybrid Search (Dense + Sparse).
    """
    client = await get_async_qdrant_client()
    embeddings = get_embeddings()
    sparse_embeddings = get_sparse_embeddings()
    
    # Generate dense embedding
    dense_vector = await asyncio.get_event_loop().run_in_executor(
        None, embeddings.embed_query, query
    )
    
    # Generate sparse embedding
    sparse_vector = sparse_embeddings.embed_query(query)
    
    # Search in Qdrant using hybrid search
    search_results = await client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            {
                "query": dense_vector,
                "using": "default", # Assuming default is the dense vector name
                "limit": top_k,
            },
            {
                "query": sparse_vector,
                "using": "sparse-text",
                "limit": top_k,
            }
        ],
        query=None, # In case of RRF or other fusion, but here we can just use prefetch
        limit=top_k,
        with_payload=True
    )
    
    # Format results
    relevant_chunks = []
    for result in search_results.points:
        chunk_data = {
            "id": result.id,
            "score": result.score,
            "content": result.payload.get("page_content", ""),
            "metadata": result.payload.get("metadata", {}),
            "source": result.payload.get("metadata", {}).get("source", "Unknown"),
            "chunk_index": result.payload.get("metadata", {}).get("chunk_index", 0)
        }
        relevant_chunks.append(chunk_data)
    
    await client.close()
    return relevant_chunks

async def print_relevant_chunks(query: str, top_k: int = 5):
    chunks = await retrieve_relevant_chunks_hybrid(query, top_k)
    
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"MODE: Hybrid Search (Dense + Sparse)")
    print(f"{'='*80}\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Result #{i} (Score: {chunk['score']:.4f}) ---")
        print(f"Source: {chunk['source']}")
        print(f"Chunk Index: {chunk['chunk_index']}")
        print(f"\nContent:\n{chunk['content']}")
        print(f"\n{'='*80}\n")
    
    return chunks

if __name__ == "__main__":
    query = "How to add stock (stock inward)?"
    asyncio.run(print_relevant_chunks(query, top_k=3))
