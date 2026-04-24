import os
import shutil
import logging
import tempfile
from fastapi import UploadFile
from config import settings
from services.ingestion_utils import extract_text, chunk_text, parse_into_documents

logger = logging.getLogger(__name__)

async def process_pdf_ingestion(file: UploadFile, llm, vector_store, qdrant_client):
    temp_path = os.path.join(tempfile.gettempdir(), f"temp_{file.filename}")
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Started background ingestion for {file.filename}")
        
        raw_text = extract_text(temp_path)
        structured_text = chunk_text(llm, raw_text)
        docs = parse_into_documents(structured_text, file.filename)
        
        # Use async aadd_documents
        await vector_store.aadd_documents(docs)
        
        count = await qdrant_client.count(
            collection_name=settings.COLLECTION_NAME
        )
        logger.info(f"✅ Ingested {len(docs)} chunks. Collection total: {count.count} vectors")
        
    except Exception as e:
        logger.error(f"❌ Ingestion failed for {file.filename}: {e}", exc_info=True)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
