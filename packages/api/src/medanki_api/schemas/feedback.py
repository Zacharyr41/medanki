"""Feedback schemas for API endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class FeedbackCategory(str, Enum):
    INACCURATE = "inaccurate"
    UNCLEAR = "unclear"
    WRONG_ANSWER = "wrong_answer"
    WRONG_TOPIC = "wrong_topic"
    TOO_COMPLEX = "too_complex"
    TOO_SIMPLE = "too_simple"
    DUPLICATE = "duplicate"


class SubmitFeedbackRequest(BaseModel):
    card_id: UUID = Field(description="The ID of the card being rated")
    feedback_type: FeedbackType = Field(description="Thumbs up or thumbs down")
    categories: list[FeedbackCategory] = Field(
        default=[],
        description="Specific issues with the card",
    )
    comment: str | None = Field(
        default=None,
        description="Optional detailed feedback",
    )
    card_text: str | None = Field(
        default=None,
        description="Card text for embedding storage (optional)",
    )
    topic_id: str | None = Field(
        default=None,
        description="Topic ID for embedding storage (optional)",
    )


class SubmitCorrectionRequest(BaseModel):
    card_id: UUID = Field(description="The ID of the card being corrected")
    original_topic_id: str = Field(description="The original topic classification")
    corrected_topic_id: str = Field(description="The correct topic classification")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="User confidence in the correction",
    )
    comment: str | None = Field(
        default=None,
        description="Optional explanation",
    )


class SubmitImplicitSignalRequest(BaseModel):
    card_id: UUID = Field(description="The ID of the card")
    view_time_ms: int = Field(default=0, ge=0, description="Time spent viewing card")
    flip_count: int = Field(default=0, ge=0, description="Number of card flips")
    scroll_depth: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Scroll depth percentage",
    )
    edit_attempted: bool = Field(default=False, description="User tried to edit")
    copy_attempted: bool = Field(default=False, description="User tried to copy")
    skipped: bool = Field(default=False, description="Card was skipped")


class FeedbackResponse(BaseModel):
    id: UUID
    card_id: UUID
    user_id: str
    feedback_type: FeedbackType
    categories: list[FeedbackCategory]
    comment: str | None
    created_at: datetime


class CorrectionResponse(BaseModel):
    id: UUID
    card_id: UUID
    user_id: str
    original_topic_id: str
    corrected_topic_id: str
    confidence: float
    comment: str | None
    created_at: datetime


class ImplicitSignalResponse(BaseModel):
    id: UUID
    card_id: UUID
    user_id: str
    view_time_ms: int
    flip_count: int
    scroll_depth: float
    edit_attempted: bool
    copy_attempted: bool
    skipped: bool
    created_at: datetime


class FeedbackAggregateResponse(BaseModel):
    card_id: UUID
    total_thumbs_up: int
    total_thumbs_down: int
    approval_rate: float
    avg_view_time_ms: float
    correction_count: int
    most_common_categories: list[FeedbackCategory]
    needs_review: bool


class FeedbackStatsResponse(BaseModel):
    total_feedback: int
    positive_count: int
    negative_count: int
    approval_rate: float
    total_corrections: int
    top_correction_patterns: list[dict]


class CorrectionPatternResponse(BaseModel):
    original_topic_id: str
    corrected_topic_id: str
    count: int
