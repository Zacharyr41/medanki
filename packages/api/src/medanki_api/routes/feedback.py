"""Feedback API routes for card quality and taxonomy correction."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from medanki.models.feedback import FeedbackCategory as CoreCategory
from medanki.models.feedback import FeedbackType as CoreType
from medanki.services.feedback import FeedbackService
from medanki_api.schemas.feedback import (
    CorrectionResponse,
    FeedbackAggregateResponse,
    FeedbackCategory,
    FeedbackResponse,
    FeedbackStatsResponse,
    FeedbackType,
    ImplicitSignalResponse,
    SubmitCorrectionRequest,
    SubmitFeedbackRequest,
    SubmitImplicitSignalRequest,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])

DB_PATH = Path("data/feedback.db")


def _get_feedback_service() -> FeedbackService:
    return FeedbackService(DB_PATH)


def _get_user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID", "anonymous")
    return user_id


@router.post(
    "/explicit",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_explicit_feedback(
    body: SubmitFeedbackRequest,
    request: Request,
) -> FeedbackResponse:
    """Submit explicit feedback (thumbs up/down) for a card."""
    user_id = _get_user_id(request)

    core_type = CoreType(body.feedback_type.value)
    core_categories = [CoreCategory(c.value) for c in body.categories]

    async with _get_feedback_service() as service:
        feedback = await service.submit_feedback(
            card_id=body.card_id,
            user_id=user_id,
            feedback_type=core_type,
            categories=core_categories,
            comment=body.comment,
            card_text=body.card_text,
            topic_id=body.topic_id,
        )

    return FeedbackResponse(
        id=feedback.id,
        card_id=feedback.card_id,
        user_id=feedback.user_id,
        feedback_type=FeedbackType(feedback.feedback_type.value),
        categories=[FeedbackCategory(c.value) for c in feedback.categories],
        comment=feedback.comment,
        created_at=feedback.created_at,
    )


@router.post(
    "/correction",
    response_model=CorrectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_taxonomy_correction(
    body: SubmitCorrectionRequest,
    request: Request,
) -> CorrectionResponse:
    """Submit a taxonomy correction for a card."""
    user_id = _get_user_id(request)

    async with _get_feedback_service() as service:
        correction = await service.submit_correction(
            card_id=body.card_id,
            user_id=user_id,
            original_topic_id=body.original_topic_id,
            corrected_topic_id=body.corrected_topic_id,
            confidence=body.confidence,
            comment=body.comment,
        )

    return CorrectionResponse(
        id=correction.id,
        card_id=correction.card_id,
        user_id=correction.user_id,
        original_topic_id=correction.original_topic_id,
        corrected_topic_id=correction.corrected_topic_id,
        confidence=correction.confidence,
        comment=correction.comment,
        created_at=correction.created_at,
    )


@router.post(
    "/implicit",
    response_model=ImplicitSignalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_implicit_signal(
    body: SubmitImplicitSignalRequest,
    request: Request,
) -> ImplicitSignalResponse:
    """Submit implicit behavioral signals for a card."""
    user_id = _get_user_id(request)

    async with _get_feedback_service() as service:
        signal = await service.submit_implicit_signal(
            card_id=body.card_id,
            user_id=user_id,
            view_time_ms=body.view_time_ms,
            flip_count=body.flip_count,
            scroll_depth=body.scroll_depth,
            edit_attempted=body.edit_attempted,
            copy_attempted=body.copy_attempted,
            skipped=body.skipped,
        )

    return ImplicitSignalResponse(
        id=signal.id,
        card_id=signal.card_id,
        user_id=signal.user_id,
        view_time_ms=signal.view_time_ms,
        flip_count=signal.flip_count,
        scroll_depth=signal.scroll_depth,
        edit_attempted=signal.edit_attempted,
        copy_attempted=signal.copy_attempted,
        skipped=signal.skipped,
        created_at=signal.created_at,
    )


@router.get(
    "/cards/{card_id}",
    response_model=FeedbackAggregateResponse,
)
async def get_card_feedback_aggregate(card_id: UUID) -> FeedbackAggregateResponse:
    """Get aggregated feedback for a specific card."""
    async with _get_feedback_service() as service:
        aggregate = await service.get_card_aggregate(card_id)

    return FeedbackAggregateResponse(
        card_id=aggregate.card_id,
        total_thumbs_up=aggregate.total_thumbs_up,
        total_thumbs_down=aggregate.total_thumbs_down,
        approval_rate=aggregate.approval_rate,
        avg_view_time_ms=aggregate.avg_view_time_ms,
        correction_count=aggregate.correction_count,
        most_common_categories=[
            FeedbackCategory(c.value) for c in aggregate.most_common_categories
        ],
        needs_review=aggregate.needs_review,
    )


@router.get(
    "/cards/{card_id}/history",
    response_model=list[FeedbackResponse],
)
async def get_card_feedback_history(card_id: UUID) -> list[FeedbackResponse]:
    """Get all feedback for a specific card."""
    async with _get_feedback_service() as service:
        feedbacks = await service.get_card_feedback(card_id)

    return [
        FeedbackResponse(
            id=f.id,
            card_id=f.card_id,
            user_id=f.user_id,
            feedback_type=FeedbackType(f.feedback_type.value),
            categories=[FeedbackCategory(c.value) for c in f.categories],
            comment=f.comment,
            created_at=f.created_at,
        )
        for f in feedbacks
    ]


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
)
async def get_feedback_stats() -> FeedbackStatsResponse:
    """Get overall feedback statistics."""
    async with _get_feedback_service() as service:
        stats = await service.get_stats()

    return FeedbackStatsResponse(
        total_feedback=stats.total_feedback,
        positive_count=stats.positive_count,
        negative_count=stats.negative_count,
        approval_rate=stats.approval_rate,
        total_corrections=stats.total_corrections,
        top_correction_patterns=stats.top_correction_patterns,
    )


@router.get(
    "/review-queue",
    response_model=list[UUID],
)
async def get_cards_needing_review(
    min_feedback: Annotated[int, Query(ge=1)] = 5,
    max_approval_rate: Annotated[float, Query(ge=0.0, le=1.0)] = 0.4,
) -> list[UUID]:
    """Get list of cards that need review based on negative feedback."""
    async with _get_feedback_service() as service:
        cards = await service.get_cards_needing_review(min_feedback, max_approval_rate)
    return cards


@router.get(
    "/high-quality",
    response_model=list[UUID],
)
async def get_high_quality_cards(
    min_feedback: Annotated[int, Query(ge=1)] = 3,
    min_approval_rate: Annotated[float, Query(ge=0.0, le=1.0)] = 0.8,
) -> list[UUID]:
    """Get list of high-quality cards based on positive feedback."""
    async with _get_feedback_service() as service:
        cards = await service.get_high_quality_cards(min_feedback, min_approval_rate)
    return cards


@router.get(
    "/correction-patterns",
    response_model=list[dict],
)
async def get_correction_patterns() -> list[dict]:
    """Get common taxonomy correction patterns for training data."""
    async with _get_feedback_service() as service:
        patterns = await service.get_correction_patterns()
    return patterns
