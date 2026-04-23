import asyncio
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse
from qdrant_client import AsyncQdrantClient
from config import settings
from embedding import get_ollama_embedding_model

async def manual_ingest_chunk(text: str, source: str = "manual_entry", metadata: dict = None):
    """
    Manually ingests a single text chunk into Qdrant using Hybrid Search settings.
    """
    print("Initializing models and client...")
    
    # 1. Initialize Models (Matches main.py)
    dense_embeddings = get_ollama_embedding_model()
    try:
        sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
    except ImportError:
        print("❌ Error: 'fastembed' package not found in the current environment.")
        print("Please run: pip install fastembed")
        return
    except Exception as e:
        print(f"❌ Error initializing Sparse Embeddings: {e}")
        return
    
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
    Q: How do I access the EPIS dashboard?
    A: To access the EPIS dashboard, log in with your credentials at https://epis.gov.bt and 
    click on the 'Dashboard' icon on the left sidebar.
    """
    
    metadata = {
        "category": "navigation",
        "importance": "high"
    }
    
    # Run the ingestion
    asyncio.run(manual_ingest_chunk(
        text=text_to_ingest, 
        source="manual_script.py", 
        metadata=metadata
    ))
