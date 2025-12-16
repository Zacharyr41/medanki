"""API route definitions."""

from medanki_api.routes.download import router as download_router
from medanki_api.routes.feedback import router as feedback_router
from medanki_api.routes.jobs import router as jobs_router
from medanki_api.routes.preview import router as preview_router
from medanki_api.routes.taxonomy import router as taxonomy_router
from medanki_api.routes.upload import router as upload_router

__all__ = [
    "jobs_router",
    "upload_router",
    "preview_router",
    "download_router",
    "feedback_router",
    "taxonomy_router",
]
