import sys
import shutil
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client.http.exceptions import UnexpectedResponse
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse
from langchain_core.prompts import ChatPromptTemplate

# Internal modules
from config import settings
from llm import get_llm
from embedding import get_ollama_embedding_model
from ingestion import extract_text, chunk_text, parse_into_documents
from qdrant import get_qdrant_client, init_collection, get_vector_store
from fastapi import UploadFile, File, BackgroundTasks
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import tempfile

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

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
        client = get_qdrant_client()
        init_collection(client)
        
        app.state.vector_store = get_vector_store(
            client, 
            app.state.ollama_embedding, 
            app.state.sparse_embedding
        )
        app.state.qdrant_client = client
        logger.info("✅ Qdrant Vector Store initialized.")

    except Exception as e:
        logger.error(f"❌ CRITICAL: Qdrant setup failed: {e}")
        sys.exit(1)

    yield
    # Cleanup
    app.state.qdrant_client.close()
    logger.info("Shutting down EPIS Chat API...")



app = FastAPI(title="EPIS Chat API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://epis.huddymerrabuddy2003.workers.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        description="The user's question about the EPIS system."
    )

async def generate_llm_stream(llm, full_prompt):
    try:
        async for chunk in llm.astream(full_prompt):
            if chunk.content:
                yield chunk.content

    except Exception as e:
        logger.error(f"Async LLM Stream error: {e}")
        yield "\n\n[ERROR: The AI generation was interrupted.]"

@app.post("/ingest")
async def ingest_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    temp_path = os.path.join(tempfile.gettempdir(), f"temp_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    async def process_and_cleanup():
        try:
            logger.info(f"Started background ingestion for {file.filename}")
           
            raw_text = extract_text(temp_path)
            llm = request.app.state.llm
            structured_text = chunk_text(llm, raw_text)
            docs = parse_into_documents(structured_text, file.filename)
            
            vector_store = request.app.state.vector_store

            # Use async aadd_documents
            await vector_store.aadd_documents(docs)
            
            count = request.app.state.qdrant_client.count(
                collection_name=settings.COLLECTION_NAME
            )
            logger.info(f"✅ Ingested {len(docs)} chunks. Collection total: {count.count} vectors")
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed for {file.filename}: {e}", exc_info=True)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    background_tasks.add_task(process_and_cleanup)

    return {
        "message": f"File '{file.filename}' uploaded successfully. Processing started in background.",
        "status": "processing"
    }

@app.post("/chat")
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    try:
        vector_store = request.app.state.vector_store
        llm = request.app.state.llm
        query_text = chat_request.query # LangChain handles the search query formatting internally for Hybrid
    
        try:
            # Hybrid search is performed by default because we set retrieval_mode=HYBRID
            retrieved_results_with_scores = await vector_store.asimilarity_search_with_score(
                query_text, 
                k=settings.TOP_K
            )
            
        except Exception as e:
            logger.error(f"Async Retrieval Failed: {e}")
            raise HTTPException(status_code=503, detail="Database unreachable.")

        content_list = []
        for doc, score in retrieved_results_with_scores:
            text_content = doc.page_content
            source = doc.metadata.get("source", "Unknown")
            formatted_content = f"[Source: {source}]\n{text_content}"
            content_list.append(formatted_content)

        if not content_list:
            logger.warning("No relevant context found for query")
            context_text = "No relevant information found in the EPIS documentation."
            logger.info(f"Final context length: {len(context_text)} characters (0 chunks)")
        else:
            # Safer truncation: Build context chunk by chunk within the limit
            context_parts = []
            current_length = 0
            for part in content_list:
                if current_length + len(part) + 5 > settings.MAX_CONTEXT_CHARS:
                    logger.warning(f"Context limit reached. Truncating remaining {len(content_list) - len(context_parts)} chunks.")
                    break
                context_parts.append(part)
                current_length += len(part) + 5 # +5 for the join separator
            
            context_text = "\n\n---\n\n".join(context_parts)
            if len(context_parts) < len(content_list):
                 context_text += "\n\n[Context truncated for length...]"
            
            logger.info(f"Final context length: {len(context_text)} characters ({len(context_parts)} chunks)")

        system_prompt = (
    "You are a specialized assistant for the Bhutan Electronic Patient Information System (EPIS). "
    "Your role is to help healthcare professionals navigate and use the EPIS system effectively.\n\n"
    "Guidelines:\n"
    "1. If the user sends a greeting (e.g., 'Hi', 'Hello', 'Kuzuzangpo'), greet them back warmly and professionally before addressing their query.\n"
    "2. Answer technical questions based ONLY on the provided context within the <context> tags.\n"
    "3. Provide step-by-step instructions when explaining procedures.\n"
    "4. If the answer is not in the context, clearly state 'Sorry I don't have that information in the EPIS documentation'.\n"
    "5. Be concise and professional.\n"
    "6. Use the exact terminology from the documentation.\n"
    "7. Format steps clearly with numbering when appropriate."
)
        
        prompt_template = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", "Context:\n<context>\n{context}\n</context>\n\nQuestion: {question}\n\nAnswer:")
        ])

        full_prompt = prompt_template.format_messages(
            context=context_text,
            question=chat_request.query
        )

        response = StreamingResponse(
            generate_llm_stream(llm, full_prompt), 
            media_type="text/plain"
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Chat Endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/debug/test-retrieval")
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

@app.delete("/debug/reset-collection")
async def reset_collection(request: Request):
    client = request.app.state.qdrant_client
    client.delete_collection(settings.COLLECTION_NAME)
    client.create_collection(
        collection_name=settings.COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        sparse_vectors_config={
            settings.SPARSE_VECTOR_NAME: SparseVectorParams()
        }
    )
    return {"message": "Collection reset. Re-ingest your PDFs with Hybrid Search support."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)