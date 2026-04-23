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

def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chunks from Qdrant based on the query.
    
    Args:
        query: User's question/query
        top_k: Number of top results to return
        
    Returns:
        List of dictionaries containing chunk content and metadata
    """
    # Generate embedding for the query
    query_embedding = embeddings.embed_query(query)
    
    # Search in Qdrant using query_points (new API) or search_points
    search_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
        with_vectors=False
    )
    
    # Format results
    relevant_chunks = []
    for result in search_results.points:
        chunk_data = {
            "id": result.id,
            "score": result.score,  # Similarity score
            "content": result.payload.get("page_content", ""),
            "metadata": result.payload.get("metadata", {}),
            "source": result.payload.get("metadata", {}).get("source", "Unknown"),
            "chunk_index": result.payload.get("metadata", {}).get("chunk_index", 0)
        }
        relevant_chunks.append(chunk_data)
    
    return relevant_chunks


def save_relevant_chunks(query: str, top_k: int = 5, output_file: str = "relevant_chunks.txt"):
    """
    Retrieve relevant chunks and save them to a file.
    
    Args:
        query: User's question/query
        top_k: Number of top results to return
        output_file: Path to output file
    """
    chunks = retrieve_relevant_chunks(query, top_k)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"QUERY: {query}\n")
        f.write("="*80 + "\n\n")
        
        for i, chunk in enumerate(chunks, 1):
            f.write(f"--- Result #{i} (Score: {chunk['score']:.4f}) ---\n")
            f.write(f"Chunk ID: {chunk['id']}\n")
            f.write(f"Source: {chunk['source']}\n")
            f.write(f"Chunk Index: {chunk['chunk_index']}\n")
            f.write(f"\nContent:\n{chunk['content']}\n")
            f.write("\n" + "="*80 + "\n\n")
    
    print(f"Successfully saved {len(chunks)} relevant chunks to {output_file}")
    return chunks


def print_relevant_chunks(query: str, top_k: int = 5):
    """
    Retrieve and print relevant chunks to console.
    
    Args:
        query: User's question/query
        top_k: Number of top results to return
    """
    chunks = retrieve_relevant_chunks(query, top_k)
    
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"{'='*80}\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Result #{i} (Similarity Score: {chunk['score']:.4f}) ---")
        print(f"Source: {chunk['source']}")
        print(f"Chunk Index: {chunk['chunk_index']}")
        print(f"\nContent:\n{chunk['content']}")
        print(f"\n{'='*80}\n")
    
    return chunks


def get_context_for_llm(query: str, top_k: int = 3) -> str:
    """
    Get formatted context to pass to LLM for RAG.
    
    Args:
        query: User's question
        top_k: Number of chunks to retrieve
        
    Returns:
        Formatted context string
    """
    chunks = retrieve_relevant_chunks(query, top_k)
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Document {i}] (Source: {chunk['source']})\n{chunk['content']}"
        )
    
    return "\n\n---\n\n".join(context_parts)


# Example usage
if __name__ == "__main__":
    # Example 1: Print to console
    query = "How to add stock (stock inward)?"
    print_relevant_chunks(query, top_k=3)
    
    # Example 2: Save to file
    # save_relevant_chunks(query, top_k=5, output_file="search_results.txt")
    
    # Example 3: Get context for LLM
    # context = get_context_for_llm(query, top_k=3)
    # print(context)