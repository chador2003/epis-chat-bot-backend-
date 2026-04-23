from qdrant_client import QdrantClient
from qdrant_client.http import models

client = QdrantClient(url="http://localhost:6333") # Adjust if in Docker

# 1. Delete the old mismatched collection
client.delete_collection(collection_name="epis_faqs")

# 2. Create it fresh for Nomic (768 dimensions)
client.create_collection(
    collection_name="epis_faqs",
    vectors_config=models.VectorParams(
        size=768, 
        distance=models.Distance.COSINE
    ),
)
print("Collection recreated successfully for 768 dimensions.")