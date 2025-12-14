"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock

import pytest


class ExamType(str, Enum):
    MCAT = "mcat"
    USMLE_STEP1 = "usmle_step1"
    USMLE_STEP2 = "usmle_step2"


class ContentType(str, Enum):
    PDF_TEXTBOOK = "pdf_textbook"
    PDF_SLIDES = "pdf_slides"
    PDF_NOTES = "pdf_notes"
    AUDIO_LECTURE = "audio_lecture"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class CardType(str, Enum):
    CLOZE = "cloze"
    VIGNETTE = "vignette"
    BASIC_QA = "basic_qa"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_MEDICAL = "invalid_medical"
    HALLUCINATION_DETECTED = "hallucination_detected"
    DUPLICATE = "duplicate"


@dataclass
class Section:
    title: str
    level: int
    start_char: int
    end_char: int
    page_number: Optional[int] = None


@dataclass
class MedicalEntity:
    text: str
    label: str
    start: int
    end: int
    cui: Optional[str] = None
    confidence: float = 1.0


@dataclass
class Document:
    id: str
    source_path: str
    content_type: ContentType
    raw_text: str
    sections: List[Section] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    page_number: Optional[int] = None
    section_path: List[str] = field(default_factory=list)
    entities: List[MedicalEntity] = field(default_factory=list)
    embedding: Optional[List[float]] = None


@dataclass
class ClozeCard:
    id: str
    text: str
    extra: str = ""
    source_chunk_id: str = ""
    tags: List[str] = field(default_factory=list)
    difficulty: str = "medium"

    CLOZE_PATTERN = re.compile(r"\{\{c\d+::([^}]+)\}\}")
    MAX_ANSWER_WORDS = 4

    def validate(self) -> tuple[bool, list[str]]:
        issues = []
        deletions = self.CLOZE_PATTERN.findall(self.text)
        if not deletions:
            issues.append("Missing cloze deletion syntax")
        for answer in deletions:
            if len(answer.split()) > self.MAX_ANSWER_WORDS:
                issues.append(f"Answer too long: {answer}")
        return len(issues) == 0, issues


@dataclass
class VignetteCard:
    id: str
    front: str
    answer: str
    explanation: str
    distinguishing_feature: Optional[str] = None
    source_chunk_id: str = ""
    tags: List[str] = field(default_factory=list)


@pytest.fixture
def sample_document() -> Document:
    return Document(
        id="doc_001",
        source_path="/data/lecture_01.pdf",
        content_type=ContentType.PDF_SLIDES,
        raw_text="Sample medical content about cardiovascular system.",
        sections=[
            Section(title="Introduction", level=1, start_char=0, end_char=50)
        ],
        metadata={"page_count": 10}
    )


@pytest.fixture
def sample_chunk() -> Chunk:
    return Chunk(
        id="chunk_001",
        document_id="doc_001",
        text="The cardiac cycle consists of systole and diastole phases.",
        start_char=0,
        end_char=57,
        token_count=12,
        page_number=1,
        section_path=["Cardiovascular", "Physiology"]
    )


@pytest.fixture
def sample_medical_text() -> str:
    return """
    Congestive heart failure (CHF) is a chronic progressive condition
    that affects the pumping power of the heart muscles. The left ventricle
    is unable to pump blood efficiently to meet the body's needs.

    Treatment includes ACE inhibitors such as lisinopril, beta-blockers
    like metoprolol, and diuretics including furosemide.
    """


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    client = AsyncMock()
    client.generate.return_value = "Generated response"
    return client
