"""Feedback models for card quality and taxonomy correction tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


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


@dataclass
class CardFeedback:
    card_id: UUID
    user_id: str
    feedback_type: FeedbackType
    id: UUID = field(default_factory=uuid4)
    categories: list[FeedbackCategory] = field(default_factory=list)
    comment: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaxonomyCorrection:
    card_id: UUID
    user_id: str
    original_topic_id: str
    corrected_topic_id: str
    id: UUID = field(default_factory=uuid4)
    confidence: float = 1.0
    comment: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ImplicitSignal:
    card_id: UUID
    user_id: str
    id: UUID = field(default_factory=uuid4)
    view_time_ms: int = 0
    flip_count: int = 0
    scroll_depth: float = 0.0
    edit_attempted: bool = False
    copy_attempted: bool = False
    skipped: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FeedbackAggregate:
    card_id: UUID
    total_thumbs_up: int = 0
    total_thumbs_down: int = 0
    avg_view_time_ms: float = 0.0
    correction_count: int = 0
    most_common_categories: list[FeedbackCategory] = field(default_factory=list)

    @property
    def approval_rate(self) -> float:
        total = self.total_thumbs_up + self.total_thumbs_down
        if total == 0:
            return 0.0
        return self.total_thumbs_up / total

    @property
    def needs_review(self) -> bool:
        total = self.total_thumbs_up + self.total_thumbs_down
        return total >= 5 and self.approval_rate < 0.4
