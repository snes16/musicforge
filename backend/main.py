import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from api.middleware import LoggingMiddleware, ErrorHandlingMiddleware
from api.routes import generate, tasks, models, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("musicforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.audio_output_dir, exist_ok=True)
    logger.info(f"MusicForge backend starting. Mock GPU: {settings.mock_gpu}, Mock ACE-Step: {settings.mock_acestep}")
    yield
    # Shutdown
    from core.acestep_client import acestep_client
    await acestep_client.close()
    logger.info("MusicForge backend shutting down.")


app = FastAPI(
    title="MusicForge API",
    description="AI Music Generation Platform powered by ACE-Step v1.5",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (order matters — outermost added last)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(models.router, prefix="/api", tags=["models"])
app.include_router(health.router, tags=["health"])

# Serve audio files as static
audio_dir = settings.audio_output_dir
os.makedirs(audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")
