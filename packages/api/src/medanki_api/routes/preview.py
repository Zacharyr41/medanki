from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from medanki_api.schemas.preview import CardPreview, PreviewResponse

router = APIRouter()

_store = None


def get_store():
    return _store


def set_store(store):
    global _store
    _store = store


def _parse_card_content(card: dict) -> dict:
    content = card.get("content", "{}")
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"text": content}
    return content


def _parse_tags(card: dict) -> list[str]:
    tags = card.get("tags", "[]")
    if isinstance(tags, str):
        try:
            return json.loads(tags)
        except json.JSONDecodeError:
            return []
    return tags if tags else []


def _extract_topics(tags: list[str]) -> list[str]:
    topic_patterns = ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B"]
    topics = []
    for tag in tags:
        for pattern in topic_patterns:
            if pattern in tag:
                topics.append(pattern)
                break
        else:
            if tag not in ["cardiology", "anatomy", "physiology", "emergency", "neurology"]:
                continue
            topics.append(tag)
    return list(set(topics)) if topics else tags[:3]


def _card_to_preview(card: dict) -> CardPreview:
    content = _parse_card_content(card)
    tags = _parse_tags(card)
    topics = _extract_topics(tags)
    card_type = card.get("card_type", "cloze")

    if card_type == "vignette":
        return CardPreview(
            id=card["id"],
            type=card_type,
            text=content.get("front", ""),
            tags=tags,
            topics=topics,
            status=card.get("status", "pending"),
            source=content.get("source"),
            front=content.get("front"),
            answer=content.get("answer"),
            explanation=content.get("explanation"),
            distinguishing_feature=content.get("distinguishing_feature"),
        )
    else:
        return CardPreview(
            id=card["id"],
            type=card_type,
            text=content.get("text", ""),
            tags=tags,
            topics=topics,
            status=card.get("status", "pending"),
            source=content.get("source"),
        )


@router.get("/jobs/{job_id}/preview", response_model=PreviewResponse)
async def get_job_preview(
    job_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    type: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    store = get_store()

    job = await store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not complete")

    cards = await store.get_cards_by_document(job["document_id"])

    if type:
        cards = [c for c in cards if c.get("card_type") == type]

    if topic:
        filtered = []
        for card in cards:
            tags = _parse_tags(card)
            topics = _extract_topics(tags)
            if topic in topics:
                filtered.append(card)
        cards = filtered

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
