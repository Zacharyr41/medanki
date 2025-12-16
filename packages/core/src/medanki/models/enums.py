"""Domain enumerations for MedAnki."""

from enum import Enum


class ExamType(str, Enum):
    """Standardized medical exam types for taxonomy classification."""

    MCAT = "mcat"
    USMLE_STEP1 = "usmle_step1"


class ContentType(str, Enum):
    """Supported input content formats."""

    PDF_TEXTBOOK = "pdf_textbook"
    PDF_SLIDES = "pdf_slides"
    POWERPOINT_SLIDES = "powerpoint_slides"
    AUDIO_LECTURE = "audio_lecture"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class CardType(str, Enum):
    """Anki card types supported by MedAnki."""

    CLOZE = "cloze"
    VIGNETTE = "vignette"
    BASIC_QA = "basic_qa"


class ValidationStatus(str, Enum):
    """Card validation status after quality checks."""

    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"
