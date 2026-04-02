from qdrant_client import QdrantClient

# Configuration
client = QdrantClient(url="http://localhost:6333")
COLLECTION_NAME = "epis_faqs"
OUTPUT_FILE = "chunks_output.txt"

next_page_offset = None

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    while True:
        # Retrieve chunks from Qdrant
        points, next_page_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=next_page_offset,
            with_payload=True,
            with_vectors=False
        )
        
        for point in points:
            payload = point.payload
            
            # Extract content (adjust keys based on your ingestion structure)
            # Often LangChain stores content in 'page_content'
            content = payload.get("page_content", "No content found")
            metadata = payload.get("metadata", {})
            source = metadata.get("source", "Unknown Source")
            
            # Write to file with formatting
            f.write(f"--- Chunk ID: {point.id} ---\n")
            f.write(f"Source: {source}\n")
            f.write(f"Content:\n{content}\n")
            f.write("\n" + "="*50 + "\n\n")
            
        if next_page_offset is None:
            break

print(f"Successfully saved all chunks to {OUTPUT_FILE}")