import sys
import shutil
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate

# Internal modules
from config import settings
from llm import get_llm
from embedding import get_ollama_embedding_model
from ingestion import extract_text, chunk_text, parse_into_documents
from fastapi import UploadFile, File, BackgroundTasks
from qdrant_client.http.models import Distance, VectorParams

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
        logger.info("✅ Models initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize models: {e}")
        sys.exit(1)

    try:
        client = QdrantClient(url=settings.QDRANT_HOST, timeout=30.0)
        
        collections_response = client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]
        
        if settings.COLLECTION_NAME not in existing_collections:
            logger.info(f"Empty/Missing collection. Initializing '{settings.COLLECTION_NAME}'...")
            
            client.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            logger.info(f"✅ Created new collection: {settings.COLLECTION_NAME}")
        else:
            logger.info(f"✅ Verified existing Qdrant collection: {settings.COLLECTION_NAME}")

        # Establish the Vector Store
        app.state.vector_store = QdrantVectorStore(
            client=client,
            collection_name=settings.COLLECTION_NAME,
            embedding=app.state.ollama_embedding,
        )

    except Exception as e:
        logger.error(f"❌ CRITICAL: Qdrant setup failed: {e}")
        sys.exit(1)

    yield
    logger.info("Shutting down EPIS Chat API...")

app = FastAPI(title="EPIS Chat API", lifespan=lifespan)

class ChatRequest(BaseModel):

    # ... Field is required
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
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    async def process_and_cleanup():
        try:
            logger.info(f"Started background ingestion for {file.filename}")
           
            raw_text = extract_text(temp_path)
            
            llm = request.app.state.llm
            structured_text =  chunk_text(llm, raw_text)
            
            docs = parse_into_documents(structured_text, file.filename)
            
            vector_store = request.app.state.vector_store
        
            vector_store.add_documents(docs)
            
            logger.info(f"✅ Successfully ingested {len(docs)} chunks from {file.filename}")
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed for {file.filename}: {e}")
        finally:
            # Always clean up the temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 4. Run the heavy processing in the background
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

        try:
            # We use await here to let other requests process while we wait for Qdrant
            retrieved_results = await vector_store.asimilarity_search(
                chat_request.query, 
                k=settings.TOP_K
            )

            print(retrieved_results)
            
        except Exception as e:
            logger.error(f"Async Retrieval Failed: {e}")
            raise HTTPException(status_code=503, detail="Database unreachable.")

        content_list = []
        for doc in retrieved_results:
            text_content = doc.page_content
            content_list.append(text_content)

        context_text = "\n\n".join(content_list)
        
        if len(context_text) > int(settings.MAX_CONTEXT_CHARS):
            logger.warning(f"Context length ({len(context_text)}) exceeds limit. Truncating.")
            context_text = context_text[:settings.MAX_CONTEXT_CHARS] + "\n\n[Context truncated for length...]"

        #Prompt Hardening with XML tags
        system_prompt = (
            "You are a specialized assistant for the Bhutan EPIS. "
            "Answer the question based ONLY on the provided context inside the XML tags. "
            "If the answer is not in the context, say you do not know."
        )
        
        prompt_template = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", "Context:\n<context>\n{context}\n</context>\n\nQuestion: {question}")
        ])

        full_prompt = prompt_template.format_messages(
            context=context_text,
            question=chat_request.query
        )
        return StreamingResponse(
            generate_llm_stream(llm, full_prompt), 
            media_type="text/plain"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Chat Endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)