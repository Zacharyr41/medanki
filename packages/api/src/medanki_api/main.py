"""FastAPI application for MedAnki API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from medanki_api.routes import jobs_router, upload_router
from medanki_api.schemas.responses import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during the application's active lifetime.
    """
    # Startup: Initialize job storage
    app.state.job_storage = {}
    yield
    # Shutdown: Clean up resources
    app.state.job_storage.clear()


app = FastAPI(
    title="MedAnki API",
    description="API for converting medical education materials into Anki flashcards",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(jobs_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions globally.

    Args:
        request: The FastAPI request object.
        exc: The exception that was raised.

    Returns:
        A JSON error response.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An unexpected error occurred",
            code="internal_error",
        ).model_dump(),
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Check API health status.

    Returns:
        A dictionary with the health status.
    """
    return {"status": "healthy"}


@app.get("/api/health", tags=["health"])
async def api_health_check() -> dict[str, str]:
    """Check API health status (with /api prefix).

    Returns:
        A dictionary with the health status.
    """
    return {"status": "healthy"}
