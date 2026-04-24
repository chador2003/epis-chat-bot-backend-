# Find the exact chunk
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from langchain_ollama import OllamaEmbeddings
from typing import List, Dict, Any

# Configuration
client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "epis_faqs"
EMBEDDING_MODEL = "nomic-embed-text"  # Same model used during ingestion

# Initialize embeddings (must match the model used during ingestion)
embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url="http://localhost:11434"
)
all_points, _ = client.scroll(
    collection_name="epis_faqs",
    limit=1000,
    with_payload=True
)

for point in all_points:
    content = point.payload.get("page_content", "")
    if "Dialysis Dashboard" in content and "How to access" in content:
        print(f"✅ FOUND THE CHUNK!")
        print(f"ID: {point.id}")
        print(f"Content:\n{content}")
        print(f"\nNow testing retrieval...")
        
        # Test if this chunk comes up in search
        test_query = "How to access Dialysis Dashboard?"
        test_embedding = embeddings.embed_query(test_query)
        test_results = client.query_points(
            collection_name="epis_faqs",
            query=test_embedding,
            limit=10
        )
        
        for i, r in enumerate(test_results.points, 1):
            if r.id == point.id:
                print(f"✅ Chunk found at position #{i} with score {r.score:.4f}")
                break
        else:
            print(f"❌ Chunk NOT in top 10 results!")