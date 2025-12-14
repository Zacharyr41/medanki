from __future__ import annotations

from fastapi import FastAPI

from medanki_api.routes.download import router as download_router
from medanki_api.routes.preview import router as preview_router

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
            "name": "health",
            "description": "API health and status checks",
        },
    ],
)

app.include_router(preview_router, prefix="/api", tags=["preview"])
app.include_router(download_router, prefix="/api", tags=["download"])


@app.get("/health", tags=["health"])
async def health_check():
    """Check API health status."""
    return {"status": "healthy"}
