from fastapi import APIRouter, Request, HTTPException
from schemas.chat import ChatRequest
from services.chat_service import get_chat_response
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat")
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    try:
        vector_store = request.app.state.vector_store
        llm = request.app.state.llm
        
        return await get_chat_response(vector_store, llm, chat_request.query)
        
    except Exception as e:
        logger.error(f"Unexpected error in Chat Endpoint: {e}")
        if "Database unreachable" in str(e):
             raise HTTPException(status_code=503, detail="Database unreachable.")
        raise HTTPException(status_code=500, detail="Internal Server Error")
