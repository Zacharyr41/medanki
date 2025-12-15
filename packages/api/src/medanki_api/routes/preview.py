from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from medanki_api.schemas.preview import CardPreview, PreviewResponse

router = APIRouter()


def _card_to_preview(card: dict) -> CardPreview:
    """Convert a card dict to CardPreview model."""
    card_type = card.get("type", "cloze")
    text = card.get("text", "")
    topic_id = card.get("topic_id")

    tags = card.get("tags", [])
    if not tags and topic_id:
        tags = [topic_id]

    topics = [topic_id] if topic_id else []

    return CardPreview(
        id=card.get("id", ""),
        type=card_type,
        text=text,
        tags=tags,
        topics=topics,
        status=card.get("status", "generated"),
        source=card.get("source_chunk"),
        front=card.get("front"),
        answer=card.get("answer"),
        explanation=card.get("explanation"),
        distinguishing_feature=card.get("distinguishing_feature"),
    )


@router.get("/jobs/{job_id}/preview", response_model=PreviewResponse)
async def get_job_preview(
    request: Request,
    job_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    type: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """Get preview of generated cards for a job."""
    job_storage = getattr(request.app.state, "job_storage", {})

    job = job_storage.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Job not complete")

    cards = job.get("cards", [])

    if type:
        cards = [c for c in cards if c.get("type") == type]

    if topic:
        cards = [c for c in cards if c.get("topic_id") == topic]

    if status:
        cards = [c for c in cards if c.get("status") == status]

    total = len(cards)
    paginated_cards = cards[offset : offset + limit]
    preview_cards = [_card_to_preview(c) for c in paginated_cards]

    return PreviewResponse(
        cards=preview_cards,
        total=total,
        limit=limit,
        offset=offset,
    )
