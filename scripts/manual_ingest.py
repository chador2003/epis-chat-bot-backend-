import asyncio
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, FastEmbedSparseProvider
from qdrant_client import AsyncQdrantClient
from config import settings
from core.embedding import get_ollama_embedding_model

async def manual_ingest_chunk(text: str, source: str = "manual_entry", metadata: dict = None):
    """
    Manually ingests a single text chunk into Qdrant using Hybrid Search settings.
    """
    print("Initializing models and client...")
    
    # 1. Initialize Models (Matches main.py)
    dense_embeddings = get_ollama_embedding_model()
    sparse_embeddings = FastEmbedSparseProvider(model_name="Qdrant/bm25")
    
    # 2. Initialize Async Client
    client = AsyncQdrantClient(
        url=settings.QDRANT_HOST,
        timeout=30.0
    )
    
    # 3. Initialize Vector Store
    # We use the same configuration as the API to ensure data is stored correctly
    vector_store = QdrantVectorStore(
        async_client=client,
        collection_name=settings.COLLECTION_NAME,
        embedding=dense_embeddings,
        sparse_embedding=sparse_embeddings,
        sparse_vector_name="sparse-text",
        retrieval_mode=QdrantVectorStore.HYBRID
    )
    
    # 4. Prepare Document
    if metadata is None:
        metadata = {}
    
    # Ensure source is always in metadata
    if "source" not in metadata:
        metadata["source"] = source
    
    doc = Document(page_content=text, metadata=metadata)
    
    # 5. Upsert
    try:
        print(f"Adding chunk to collection '{settings.COLLECTION_NAME}'...")
        await vector_store.aadd_documents([doc])
        
        # Verify
        count = await client.count(collection_name=settings.COLLECTION_NAME)
        print(f"✅ Success! Collection total count: {count.count}")
        
    except Exception as e:
        print(f"❌ Failed to ingest: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    # --- CONFIGURE YOUR CHUNK HERE ---
    text_to_ingest = """
        Q. How to Upload Supporting Documents in Grievance Registration?
        A. To upload supporting documents in Grievance Registration, follow these steps:
            1. Click the Choose File button.
            2. Select the required file from your computer.
            3. Click Add to upload document.
            4. Click View Documents to verify the uploaded files.
            Supporting documents may include:
            * Photos
            * PDF files
            * Other relevant evidence.
    
    """
    
    metadata = {
        "category": "grievance_management",
        "importance": "high"
    }
    
    # Run the ingestion
    asyncio.run(manual_ingest_chunk(
        text=text_to_ingest, 
        source="manual_script.py", 
        metadata=metadata
    ))
