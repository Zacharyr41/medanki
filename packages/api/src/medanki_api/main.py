"""FastAPI application for MedAnki API."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from medanki.storage.sqlite import SQLiteStore
from medanki.storage.user_repository import UserRepository
from medanki_api.routes import feedback_router, jobs_router, taxonomy_router, upload_router
from medanki_api.routes.auth import router as auth_router
from medanki_api.routes.download import router as download_router
from medanki_api.routes.preview import router as preview_router
from medanki_api.routes.saved_cards import router as saved_cards_router
from medanki_api.schemas.responses import ErrorResponse
from medanki_api.websocket.routes import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None during the application's active lifetime.
    """
    app.state.job_storage = {}
    sqlite_store = SQLiteStore("medanki.db")
    await sqlite_store.initialize()
    app.state.sqlite_store = sqlite_store
    app.state.user_repository = UserRepository(sqlite_store)
    yield
    app.state.job_storage.clear()
    await sqlite_store.close()


app = FastAPI(
    title="MedAnki API",
    description="""
## Medical Flashcard Generation API

MedAnki transforms medical documents into Anki-compatible flashcards with AI-powered classification.

### Features

* **Document Processing** - Upload and process medical content
* **Smart Classification** - Automatic MCAT/USMLE topic tagging
* **Card Preview** - Review generated cards with filtering
* **Deck Export** - Download .apkg files for Anki

### Card Types

* **Cloze** - Fill-in-the-blank cards for memorization
* **Vignette** - Clinical case-based questions
* **Basic Q&A** - Simple question and answer format
    """,
    version="0.1.0",
    contact={
        "name": "MedAnki Support",
        "url": "https://github.com/your-org/medanki",
    },
    license_info={
        "name": "GPL-3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
    },
    openapi_tags=[
        {
            "name": "preview",
            "description": "Card preview and filtering operations",
        },
        {
            "name": "download",
            "description": "Deck download, regeneration, and statistics",
        },
        {
            "name": "feedback",
            "description": "Card quality feedback and taxonomy corrections",
        },
        {
            "name": "health",
            "description": "API health and status checks",
        },
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(saved_cards_router, prefix="/api/saved-cards", tags=["saved_cards"])
app.include_router(preview_router, prefix="/api", tags=["preview"])
app.include_router(download_router, prefix="/api", tags=["download"])
app.include_router(taxonomy_router, prefix="/api", tags=["taxonomy"])
app.include_router(feedback_router, prefix="/api", tags=["feedback"])
app.include_router(websocket_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions globally."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An unexpected error occurred",
            code="internal_error",
        ).model_dump(),
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Check API health status."""
    return {"status": "healthy"}


@app.get("/api/health", tags=["health"])
async def api_health_check() -> dict[str, str]:
    """Check API health status (with /api prefix)."""
    return {"status": "healthy"}
