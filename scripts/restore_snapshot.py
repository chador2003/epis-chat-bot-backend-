from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Restore from a local file on the server node
client.recover_snapshot(
    collection_name="epis_faqs",
    location=r"C:\Users\Admin\Downloads\epis_faqs-3309418699288294-2026-06-09-10-14-46.snapshot"
)
