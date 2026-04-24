from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request, HTTPException
from services.ingestion_service import process_pdf_ingestion
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/ingest")
async def ingest_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    background_tasks.add_task(
        process_pdf_ingestion, 
        file, 
        request.app.state.llm, 
        request.app.state.vector_store, 
        request.app.state.qdrant_client
    )

    return {
        "message": f"File '{file.filename}' uploaded successfully. Processing started in background.",
        "status": "processing"
    }
