from __future__ import annotations

from fastapi import FastAPI

from medanki_api.routes.download import router as download_router
from medanki_api.routes.preview import router as preview_router

app = FastAPI(
    title="MedAnki API",
    description="API for generating and managing Anki flashcards from medical content",
    version="0.1.0",
)

app.include_router(preview_router, prefix="/api", tags=["preview"])
app.include_router(download_router, prefix="/api", tags=["download"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
