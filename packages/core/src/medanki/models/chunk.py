"""Chunk domain models for MedAnki."""

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from medanki.models.document import MedicalEntity
from medanki.models.enums import ExamType


class MatchType(str, Enum):
    """How a chunk was matched to a taxonomy topic."""

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class TopicMatch(BaseModel):
    """A taxonomy topic matched to a chunk.

    Represents the result of classifying a chunk against MCAT/USMLE
    taxonomy hierarchies using hybrid search.
    """

    topic_id: str = Field(..., min_length=1, description="Unique topic identifier")
    topic_path: str = Field(
        ..., min_length=1, description="Full hierarchical path (e.g., 'Biology > Cell Biology')"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score")
    match_type: MatchType = Field(..., description="How the match was determined")

    @field_validator("topic_path")
    @classmethod
    def topic_path_must_have_separator(cls, v: str) -> str:
        """Validate topic path contains hierarchy or is a root topic."""
        return v.strip()


class Chunk(BaseModel):
    """A text chunk extracted from a document.

    Represents a semantically coherent segment of text suitable
    for card generation, with preserved medical terminology.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique chunk identifier")
    document_id: UUID = Field(..., description="Parent document identifier")
    text: str = Field(..., min_length=1, description="Chunk text content")
    start_char: int = Field(..., ge=0, description="Start offset in document")
    end_char: int = Field(..., gt=0, description="End offset in document")
    token_count: int = Field(..., gt=0, description="Number of tokens in chunk")
    section_path: str = Field(
        default="", description="Hierarchical section path (e.g., 'Chapter 1 > Section 2')"
    )
    entities: list[MedicalEntity] = Field(
        default_factory=list, description="Medical entities in this chunk"
    )

    @model_validator(mode="after")
    def validate_char_offsets(self) -> "Chunk":
        """Validate end_char is greater than start_char."""
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        return self

    @property
    def char_count(self) -> int:
        """Return character count of chunk text."""
        return len(self.text)

    @property
    def entity_count(self) -> int:
        """Return number of medical entities in chunk."""
        return len(self.entities)


class ClassifiedChunk(BaseModel):
    """A chunk with taxonomy classifications.

    Extends a Chunk with topic matches and primary exam assignment
    after the classification pipeline.
    """

    chunk: Chunk = Field(..., description="The source chunk")
    topics: list[TopicMatch] = Field(
        default_factory=list, description="Matched taxonomy topics"
    )
    primary_exam: ExamType | None = Field(
        default=None, description="Primary exam this chunk is relevant to"
    )

    @property
    def top_topic(self) -> TopicMatch | None:
        """Return the highest confidence topic match."""
        if not self.topics:
            return None
        return max(self.topics, key=lambda t: t.confidence)

    @property
    def is_classified(self) -> bool:
        """Check if chunk has any topic classifications."""
        return len(self.topics) > 0

    def topics_above_threshold(self, threshold: float = 0.65) -> list[TopicMatch]:
        """Return topics with confidence above threshold."""
        return [t for t in self.topics if t.confidence >= threshold]
