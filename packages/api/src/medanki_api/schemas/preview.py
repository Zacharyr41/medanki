from __future__ import annotations

from pydantic import BaseModel


class CardPreview(BaseModel):
    id: str
    type: str
    text: str
    tags: list[str]
    topics: list[str]
    status: str
    source: str | None = None
    front: str | None = None
    answer: str | None = None
    explanation: str | None = None
    distinguishing_feature: str | None = None


class PreviewResponse(BaseModel):
    cards: list[CardPreview]
    total: int
    limit: int
    offset: int


class CardCounts(BaseModel):
    total: int
    cloze: int
    vignette: int
    basic_qa: int = 0


class TimingInfo(BaseModel):
    created_at: str
    completed_at: str
    duration_seconds: float


class StatsResponse(BaseModel):
    counts: CardCounts
    topics: dict[str, int]
    timing: TimingInfo


class RegenerateRequest(BaseModel):
    deck_name: str | None = None
    include_tags: list[str] | None = None
    exclude_tags: list[str] | None = None


class RegenerateResponse(BaseModel):
    job_id: str
