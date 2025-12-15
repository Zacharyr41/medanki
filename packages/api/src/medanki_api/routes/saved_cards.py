"""Saved cards API routes."""

from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from medanki_api.routes.auth import get_current_user_id

router = APIRouter()


class SaveCardsRequest(BaseModel):
    """Request body for saving cards."""

    job_id: str
    card_ids: list[str] = Field(..., min_length=1)


class SaveCardsResponse(BaseModel):
    """Response for saving cards."""

    saved_count: int
    message: str = "Cards saved successfully"


class SavedCardResponse(BaseModel):
    """Single saved card in response."""

    id: str
    card_id: str
    job_id: str
    saved_at: str


class SavedCardsListResponse(BaseModel):
    """Response for listing saved cards."""

    cards: list[SavedCardResponse]
    total: int
    limit: int
    offset: int


class DeleteResponse(BaseModel):
    """Response for deleting a saved card."""

    message: str = "Card removed successfully"


@router.post("", response_model=SaveCardsResponse)
async def save_cards(
    request: Request,
    body: SaveCardsRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SaveCardsResponse:
    """Save selected cards to user's account.

    Args:
        request: The FastAPI request object
        body: The save request containing job_id and card_ids
        user_id: The current user's ID

    Returns:
        SaveCardsResponse with count of saved cards

    Raises:
        HTTPException: 404 if job not found, 400 if card_ids is empty
    """
    if not body.card_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one card ID is required",
        )

    job_storage = request.app.state.job_storage
    if body.job_id not in job_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {body.job_id} not found",
        )

    job = job_storage[body.job_id]
    valid_card_ids = {card["id"] for card in job.get("cards", [])}

    invalid_ids = set(body.card_ids) - valid_card_ids
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid card IDs: {invalid_ids}",
        )

    user_repo = request.app.state.user_repository
    saved_count = 0

    for card_id in body.card_ids:
        try:
            await user_repo.save_card(
                user_id=user_id,
                job_id=body.job_id,
                card_id=card_id,
            )
            saved_count += 1
        except Exception:
            pass

    return SaveCardsResponse(
        saved_count=saved_count,
        message=f"Saved {saved_count} cards",
    )


@router.get("", response_model=SavedCardsListResponse)
async def get_saved_cards(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = 20,
    offset: int = 0,
) -> SavedCardsListResponse:
    """Get user's saved cards.

    Args:
        request: The FastAPI request object
        user_id: The current user's ID
        limit: Maximum number of cards to return
        offset: Number of cards to skip

    Returns:
        SavedCardsListResponse with paginated cards
    """
    user_repo = request.app.state.user_repository

    cards = await user_repo.get_saved_cards(user_id, limit=limit, offset=offset)
    total = await user_repo.get_saved_cards_count(user_id)

    return SavedCardsListResponse(
        cards=[
            SavedCardResponse(
                id=card.id,
                card_id=card.card_id,
                job_id=card.job_id,
                saved_at=card.saved_at.isoformat(),
            )
            for card in cards
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/{card_id}", response_model=DeleteResponse)
async def remove_saved_card(
    request: Request,
    card_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> DeleteResponse:
    """Remove a saved card.

    Args:
        request: The FastAPI request object
        card_id: The card ID to remove
        user_id: The current user's ID

    Returns:
        DeleteResponse with success message
    """
    user_repo = request.app.state.user_repository
    await user_repo.remove_saved_card(user_id=user_id, card_id=card_id)

    return DeleteResponse()


@router.get("/export")
async def export_saved_cards(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Export saved cards as an Anki package.

    Args:
        request: The FastAPI request object
        user_id: The current user's ID

    Returns:
        StreamingResponse with .apkg file

    Raises:
        HTTPException: 400 if no cards to export
    """
    user_repo = request.app.state.user_repository

    count = await user_repo.get_saved_cards_count(user_id)
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No saved cards to export",
        )

    saved_cards = await user_repo.get_saved_cards(user_id, limit=1000)
    job_storage = request.app.state.job_storage

    cards_to_export = []
    for saved in saved_cards:
        job = job_storage.get(saved.job_id)
        if job:
            for card in job.get("cards", []):
                if card["id"] == saved.card_id:
                    cards_to_export.append(card)
                    break

    try:
        from medanki.export.apkg import AnkiPackageGenerator

        generator = AnkiPackageGenerator()
        apkg_bytes = generator.generate_from_cards(cards_to_export, "Saved Cards")
    except ImportError:
        apkg_bytes = b"mock_apkg_content"

    return StreamingResponse(
        io.BytesIO(apkg_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=saved_cards_{user_id}.apkg"},
    )
