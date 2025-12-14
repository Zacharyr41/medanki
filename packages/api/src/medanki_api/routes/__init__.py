"""API route definitions."""

from medanki_api.routes.jobs import router as jobs_router
from medanki_api.routes.upload import router as upload_router

__all__ = ["jobs_router", "upload_router"]
