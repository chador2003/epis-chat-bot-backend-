from fastapi import APIRouter
from api.endpoints import chat, ingestion, debug

api_router = APIRouter()

api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(ingestion.router, tags=["ingestion"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
