from __future__ import annotations

import json
import tempfile
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from medanki_api.schemas.preview import (
    CardCounts,
    RegenerateRequest,
    RegenerateResponse,
    StatsResponse,
    TimingInfo,
)

router = APIRouter()


def _get_job_storage(request: Request) -> dict:
    """Get the job storage from app state."""
    if not hasattr(request.app.state, "job_storage"):
        request.app.state.job_storage = {}
    return request.app.state.job_storage


def _get_job_or_none(request: Request, job_id: str) -> dict | None:
    """Get a job by ID or return None."""
    storage = _get_job_storage(request)
    return storage.get(job_id)


@dataclass
class ClozeCardData:
    """Data class for cloze cards compatible with DeckBuilder."""

    text: str
    extra: str
    source_chunk_id: str
    tags: list[str]


@dataclass
class VignetteCardData:
    """Data class for vignette cards compatible with DeckBuilder."""

    front: str
    answer: str
    explanation: str
    distinguishing_feature: str | None
    source_chunk_id: str
    tags: list[str]


def generate_apkg(cards: list, deck_name: str = "MedAnki") -> bytes:
    """Generate a real APKG file from cards using genanki."""
    from medanki.export.apkg import APKGExporter
    from medanki.export.deck import DeckBuilder

    builder = DeckBuilder(deck_name)

    for card in cards:
        card_type = card.get("type", "cloze")
        topic_id = card.get("topic_id", "")
        source = card.get("source_chunk", "")[:100] if card.get("source_chunk") else ""
        tags = [topic_id] if topic_id else []

        if card_type == "cloze":
            cloze_data = ClozeCardData(
                text=card.get("text", ""),
                extra="",
                source_chunk_id=source,
                tags=tags,
            )
            builder.add_cloze_card(cloze_data)
        elif card_type == "vignette":
            vignette_data = VignetteCardData(
                front=card.get("text", card.get("front", "")),
                answer=card.get("answer", ""),
                explanation=card.get("explanation", ""),
                distinguishing_feature=card.get("distinguishing_feature"),
                source_chunk_id=source,
                tags=tags,
            )
            builder.add_vignette_card(vignette_data)
        else:
            cloze_data = ClozeCardData(
                text=card.get("text", ""),
                extra="",
                source_chunk_id=source,
                tags=tags,
            )
            builder.add_cloze_card(cloze_data)

    deck = builder.build()
    exporter = APKGExporter()

    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        exporter.export(deck, tmp_path)
        apkg_bytes = Path(tmp_path).read_bytes()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return apkg_bytes


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
async def download_deck(request: Request, job_id: str):
    job = _get_job_or_none(request, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not complete")

    cards = job.get("cards", [])
    apkg_content = generate_apkg(cards)

    return Response(
        content=apkg_content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="medanki_{job_id}.apkg"'},
    )


@router.post("/jobs/{job_id}/regenerate", response_model=RegenerateResponse)
async def regenerate_deck(request: Request, job_id: str, body: RegenerateRequest | None = None):
    job = _get_job_or_none(request, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    options = {}
    if body:
        if body.deck_name:
            options["deck_name"] = body.deck_name
        if body.include_tags:
            options["include_tags"] = body.include_tags
        if body.exclude_tags:
            options["exclude_tags"] = body.exclude_tags

    new_job_id = create_processing_job(job.get("document_id", job_id), options)

    return RegenerateResponse(job_id=new_job_id)


@router.get("/jobs/{job_id}/stats", response_model=StatsResponse)
async def get_job_stats(request: Request, job_id: str):
    job = _get_job_or_none(request, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not complete")

    cards = job.get("cards", [])

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
