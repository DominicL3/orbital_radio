"""FastAPI application entry point for Orbital Radio backend."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.geography import router as geography_router
from src.api.radio import router as radio_router
from src.api.satellites import router as satellites_router
from src.config import get_settings
from src.database import init_database
from src.scheduler import init_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    init_database()
    sch = init_scheduler()
    if not sch.running:
        sch.start()
    yield
    stop_scheduler()


app = FastAPI(
    title="Orbital Radio API",
    version="0.1.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(satellites_router)
app.include_router(geography_router)
app.include_router(radio_router)


@app.get("/health")
def health_check() -> dict[str, Any]:
    """Basic health check endpoint.

    Returns:
        Dict[str, Any]: Health status dictionary with timestamp.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }
