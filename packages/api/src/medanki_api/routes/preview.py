from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request

from medanki_api.schemas.preview import CardPreview, PreviewResponse, TopicInfo

router = APIRouter()

TAXONOMY_DIR = Path("data/taxonomies")


@lru_cache(maxsize=1)
def _load_topic_lookup() -> dict[str, str]:
    """Load a lookup dict mapping topic IDs to titles from taxonomy JSON files."""
    lookup: dict[str, str] = {}

    usmle_path = TAXONOMY_DIR / "usmle_step1.json"
    if usmle_path.exists():
        data = json.loads(usmle_path.read_text())
        for system in data.get("systems", []):
            sys_id = system.get("id", "")
            lookup[sys_id] = system.get("title", sys_id)
            for topic in system.get("topics", []):
                topic_id = topic.get("id", "")
                lookup[topic_id] = topic.get("title", topic_id)

    mcat_path = TAXONOMY_DIR / "mcat.json"
    if mcat_path.exists():
        data = json.loads(mcat_path.read_text())
        for fc in data.get("foundational_concepts", []):
            fc_id = fc.get("id", "")
            lookup[fc_id] = fc.get("title", fc_id)
            for cat in fc.get("categories", []):
                cat_id = cat.get("id", "")
                lookup[cat_id] = cat.get("title", cat_id)

    return lookup


def _card_to_preview(card: dict, topic_lookup: dict[str, str]) -> CardPreview:
    """Convert a card dict to CardPreview model."""
    card_type = card.get("type", "cloze")
    text = card.get("text", "")
    topic_id = card.get("topic_id")

    tags = card.get("tags", [])
    if not tags and topic_id:
        tags = [topic_id]

    topics: list[TopicInfo] = []
    if topic_id:
        topic_title = topic_lookup.get(topic_id)
        topics = [TopicInfo(id=topic_id, title=topic_title)]

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
    topic_lookup = _load_topic_lookup()
    preview_cards = [_card_to_preview(c, topic_lookup) for c in paginated_cards]

    return PreviewResponse(
        cards=preview_cards,
        total=total,
        limit=limit,
        offset=offset,
    )
