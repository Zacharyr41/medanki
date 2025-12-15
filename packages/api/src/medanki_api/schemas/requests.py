"""Request schemas for API endpoints."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class ExamType(str, Enum):
    """Supported exam types for flashcard generation."""

    MCAT = "MCAT"
    USMLE_STEP1 = "USMLE Step 1"


class CardTypeOption(str, Enum):
    """Card type options for generation."""

    CLOZE = "cloze"
    VIGNETTE = "vignette"
    BASIC_QA = "basic_qa"


class UploadRequest(BaseModel):
    """Request model for file upload options.

    These fields are submitted as form data alongside the file upload.
    """

    exam: ExamType | None = Field(
        default=None,
        description="Target exam type for flashcard generation",
    )
    card_types: str | None = Field(
        default=None,
        description="Comma-separated list of card types to generate (e.g., 'cloze,vignette')",
    )
    max_cards: Annotated[int | None, Field(ge=1, le=500)] = Field(
        default=None,
        description="Maximum number of cards to generate per document",
    )

    def get_card_types_list(self) -> list[CardTypeOption]:
        """Parse comma-separated card types into a list."""
        if not self.card_types:
            return [CardTypeOption.CLOZE]  # Default to cloze
        types = []
        for ct in self.card_types.split(","):
            ct = ct.strip().lower()
            if ct in [e.value for e in CardTypeOption]:
                types.append(CardTypeOption(ct))
        return types if types else [CardTypeOption.CLOZE]


class JobListParams(BaseModel):
    """Query parameters for listing jobs."""

    limit: Annotated[int, Field(ge=1, le=100)] = Field(
        default=20,
        description="Maximum number of jobs to return",
    )
    offset: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Number of jobs to skip",
    )
    status: str | None = Field(
        default=None,
        description="Filter jobs by status (pending, processing, completed, failed, cancelled)",
    )
