from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CardPreview(BaseModel):
    id: str
    type: str
    text: str
    tags: List[str]
    topics: List[str]
    status: str
    source: Optional[str] = None
    front: Optional[str] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    distinguishing_feature: Optional[str] = None


class PreviewResponse(BaseModel):
    cards: List[CardPreview]
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
    topics: Dict[str, int]
    timing: TimingInfo


class RegenerateRequest(BaseModel):
    deck_name: Optional[str] = None
    include_tags: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None


class RegenerateResponse(BaseModel):
    job_id: str
