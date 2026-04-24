import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.deps import lifespan
from api.router import api_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(title="EPIS Chat API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://epis.huddymerrabuddy2003.workers.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
