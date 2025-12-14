from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from medanki_api.schemas.preview import (
    CardCounts,
    RegenerateRequest,
    RegenerateResponse,
    StatsResponse,
    TimingInfo,
)

router = APIRouter()

_store = None


def get_store():
    return _store


def set_store(store):
    global _store
    _store = store


def generate_apkg(cards: list, deck_name: str = "MedAnki") -> bytes:
    return b"APKG_CONTENT"


def create_processing_job(document_id: str, options: dict) -> str:
    return f"job_{uuid.uuid4().hex[:8]}"


def _parse_tags(card: dict) -> list:
    tags = card.get("tags", "[]")
    if isinstance(tags, str):
        try:
            return json.loads(tags)
        except json.JSONDecodeError:
            return []
    return tags if tags else []


@router.get("/jobs/{job_id}/download")
async def download_deck(job_id: str):
    store = get_store()

    job = await store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not complete")

    cards = await store.get_cards_by_document(job["document_id"])
    apkg_content = generate_apkg(cards)

    return Response(
        content=apkg_content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="medanki_{job_id}.apkg"'
        },
    )


@router.post("/jobs/{job_id}/regenerate", response_model=RegenerateResponse)
async def regenerate_deck(job_id: str, request: RegenerateRequest | None = None):
    store = get_store()

    job = await store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    options = {}
    if request:
        if request.deck_name:
            options["deck_name"] = request.deck_name
        if request.include_tags:
            options["include_tags"] = request.include_tags
        if request.exclude_tags:
            options["exclude_tags"] = request.exclude_tags

    new_job_id = create_processing_job(job["document_id"], options)

    return RegenerateResponse(job_id=new_job_id)


@router.get("/jobs/{job_id}/stats", response_model=StatsResponse)
async def get_job_stats(job_id: str):
    store = get_store()

    job = await store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not complete")

    cards = await store.get_cards_by_document(job["document_id"])

    type_counter = Counter(c.get("card_type", "cloze") for c in cards)
    topic_counter: Counter = Counter()

    for card in cards:
        tags = _parse_tags(card)
        for tag in tags:
            topic_counter[tag] += 1

    created_at = job.get("created_at", "")
    completed_at = job.get("updated_at", "")

    duration_seconds = 0.0
    try:
        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        duration_seconds = (completed_dt - created_dt).total_seconds()
    except (ValueError, AttributeError):
        pass

    return StatsResponse(
        counts=CardCounts(
            total=len(cards),
            cloze=type_counter.get("cloze", 0),
            vignette=type_counter.get("vignette", 0),
            basic_qa=type_counter.get("basic_qa", 0),
        ),
        topics=dict(topic_counter),
        timing=TimingInfo(
            created_at=created_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
        ),
    )
