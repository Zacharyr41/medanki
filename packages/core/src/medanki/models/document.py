"""Document domain models for MedAnki."""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from medanki.models.enums import ContentType


class MedicalEntity(BaseModel):
    """A medical named entity extracted from text.

    Represents entities like diseases, drugs, anatomical structures,
    and procedures identified by scispaCy NER.
    """

    text: str = Field(..., min_length=1, description="The entity surface form")
    label: str = Field(..., min_length=1, description="Entity type (e.g., DISEASE, DRUG)")
    start_char: int = Field(..., ge=0, description="Start character offset in source text")
    end_char: int = Field(..., gt=0, description="End character offset in source text")
    umls_cui: str | None = Field(default=None, description="UMLS Concept Unique Identifier")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="NER confidence score")

    @field_validator("end_char")
    @classmethod
    def end_must_exceed_start(cls, v: int, info: ValidationInfo) -> int:
        """Validate end_char is greater than start_char."""
        if "start_char" in info.data and v <= info.data["start_char"]:
            raise ValueError("end_char must be greater than start_char")
        return v


class Section(BaseModel):
    """A hierarchical section within a document.

    Represents document structure like chapters, headings, and subheadings
    extracted during PDF parsing.
    """

    title: str = Field(..., min_length=1, description="Section heading text")
    content: str = Field(default="", description="Section body content")
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")
    page_numbers: list[int] = Field(default_factory=list, description="Pages where section appears")

    @field_validator("page_numbers")
    @classmethod
    def page_numbers_must_be_positive(cls, v: list[int]) -> list[int]:
        """Validate all page numbers are positive."""
        if any(p < 1 for p in v):
            raise ValueError("page numbers must be positive integers")
        return v


class Document(BaseModel):
    """A source document ingested into MedAnki.

    Represents the full extracted content from a PDF, audio transcript,
    or text file before chunking.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique document identifier")
    source_path: Path = Field(..., description="Original file path")
    content_type: ContentType = Field(..., description="Type of source content")
    raw_text: str = Field(default="", description="Full extracted text content")
    sections: list[Section] = Field(
        default_factory=list, description="Hierarchical document sections"
    )
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Extraction metadata (author, title, etc.)"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of extraction"
    )

    @field_validator("source_path")
    @classmethod
    def source_path_must_have_name(cls, v: Path) -> Path:
        """Validate source path has a filename."""
        if not v.name:
            raise ValueError("source_path must have a filename")
        return v

    @property
    def word_count(self) -> int:
        """Return approximate word count of raw text."""
        return len(self.raw_text.split())

    @property
    def has_structure(self) -> bool:
        """Check if document has hierarchical sections."""
        return len(self.sections) > 0
