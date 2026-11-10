import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.database import init_db
from app.api.v1.routes import router as api_v1_router

# Setup logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sarthi_pay")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Sarthi Pay SQLite database & seeding mock data...")
    await init_db()
    logger.info("Sarthi Pay backend startup complete.")
    yield
    logger.info("Sarthi Pay backend shutting down.")


app = FastAPI(
    title="Sarthi Pay API",
    description="Accessible, Voice-First Banking & Utility Payment Assistant for Senior Citizens",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_v1_router)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Sarthi Pay Backend",
        "version": "1.0.0",
        "indic_llm": "Evon v3.3",
        "stt_engine": "Gnani.ai Indic Streaming STT",
        "tts_engine": "Gnani Timbre v3.0 Expressive Indic"
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to Sarthi Pay Voice-First Banking API",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

