"""Cloze card generation service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID, uuid4

from medanki.models.cards import ClozeCard

if TYPE_CHECKING:
    from typing import Any


# Constants from CLAUDE.md
CLOZE_MODEL_ID = 1607392319001


@runtime_checkable
class ILLMClient(Protocol):
    """Protocol for LLM client used in cloze generation."""

    async def generate_cloze_cards(
        self,
        text: str,
        count: int = 3,
        tags: list[str] | None = None,
        topic_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate cloze cards from text.

        Args:
            text: Source text to generate cards from.
            count: Number of cards to generate.
            tags: Optional tags to include with cards.

        Returns:
            List of dictionaries with 'text' and 'tags' keys.
        """
        ...


@dataclass
class GeneratedClozeCard:
    """A generated cloze deletion card.

    Attributes:
        text: The cloze deletion text with {{c1::answer}} format.
        source_chunk_id: UUID of the source chunk for provenance tracking.
        tags: Topic tags from the classified chunk.
        id: Unique identifier for the card.
    """

    text: str
    source_chunk_id: UUID
    tags: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)

    # Validation patterns
    CLOZE_PATTERN: re.Pattern[str] = field(
        default=re.compile(r"\{\{c(\d+)::([^}]+)\}\}"),
        repr=False,
        compare=False,
    )
    MAX_ANSWER_WORDS: int = field(default=4, repr=False, compare=False)

    def is_valid(self) -> bool:
        """Check if the card has valid cloze syntax and answer length."""
        matches = list(self.CLOZE_PATTERN.finditer(self.text))
        if not matches:
            return False

        for match in matches:
            answer = match.group(2).strip()
            word_count = len(answer.split())
            if word_count < 1 or word_count > self.MAX_ANSWER_WORDS:
                return False

        return True


# Trivial words that should not be cloze deletions
TRIVIAL_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "of",
        "to",
        "and",
        "or",
        "in",
        "on",
        "at",
        "for",
        "with",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
    }
)

# Research trivia patterns that should not be cloze deletions
TRIVIA_PATTERNS = [
    re.compile(r"\b[A-Z]{2,}(?:-[A-Z]+)*\s+(?:trial|study|cohort)\b", re.IGNORECASE),
    re.compile(r"\bHR\s*[=:]\s*\d+\.?\d*"),
    re.compile(r"\bp\s*[<>=]\s*0?\.\d+"),
    re.compile(r"\b(?:19|20)\d{2}\s+(?:guidelines?|recommendations?)\b", re.IGNORECASE),
    re.compile(r"\b\d+%?\s*CI\b|\bconfidence interval\b", re.IGNORECASE),
    re.compile(r"\bRR\s*[=:]\s*\d+\.?\d*"),
    re.compile(r"\bOR\s*[=:]\s*\d+\.?\d*"),
    re.compile(r"\b\d{1,2}(?:\.\d+)?%"),
    re.compile(r"\bet\s+al\.?\b", re.IGNORECASE),
    re.compile(r"^[A-Z][a-z]+\s+\(\d{4}\)$"),
    re.compile(r"^(?:Figure|Table|Fig\.?)\s*\d+", re.IGNORECASE),
    re.compile(r"^(?:19|20)\d{2}$"),
    re.compile(r"\bPMID\s*\d+", re.IGNORECASE),
    re.compile(r"^10\.\d+/"),
]

JOURNAL_NAMES = frozenset(
    {
        "nejm",
        "lancet",
        "jama",
        "bmj",
        "nature",
        "science",
        "cell",
        "annals",
        "circulation",
        "chest",
        "gastroenterology",
    }
)


class ClozeGenerator:
    """Service for generating cloze deletion flashcards from classified chunks.

    Uses an LLM client to generate cloze cards and performs post-processing
    to validate syntax and filter invalid cards.
    """

    def __init__(self, llm_client: ILLMClient) -> None:
        """Initialize the cloze generator.

        Args:
            llm_client: LLM client for generating cloze cards.
        """
        self._llm_client = llm_client
        self._cloze_pattern = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")

    async def generate(
        self,
        content: str,
        source_chunk_id: UUID,
        topic_id: str | None = None,
        topic_context: str | None = None,
        num_cards: int = 3,
    ) -> list[ClozeCard]:
        """Generate cloze cards from content.

        Args:
            content: Text content to generate cards from.
            source_chunk_id: UUID of the source chunk.
            topic_id: Optional topic ID for tagging.
            topic_context: Optional topic path for LLM context.
            num_cards: Maximum number of cards to generate.

        Returns:
            List of validated ClozeCard objects.

        Raises:
            Exception: If the LLM client fails.
        """
        tags = [topic_id] if topic_id else []

        raw_cards = await self._llm_client.generate_cloze_cards(
            text=content,
            count=num_cards,
            tags=tags,
            topic_context=topic_context,
        )

        valid_cards: list[ClozeCard] = []
        for raw_card in raw_cards:
            card_text = raw_card.get("text", "")
            card_tags = raw_card.get("tags", tags)

            if not self._has_valid_cloze_syntax(card_text):
                continue

            if self._has_trivial_deletion(card_text):
                continue

            if self._has_long_answer(card_text):
                continue

            if self._has_trivia_deletion(card_text):
                continue

            generated = GeneratedClozeCard(
                text=card_text,
                source_chunk_id=source_chunk_id,
                tags=card_tags,
            )

            if generated.is_valid():
                valid_cards.append(
                    ClozeCard(
                        text=generated.text,
                        source_chunk_id=source_chunk_id,
                        topic_id=topic_id,
                    )
                )

        return valid_cards[:num_cards]

    def _has_valid_cloze_syntax(self, text: str) -> bool:
        """Check if text has valid cloze deletion syntax."""
        matches = self._cloze_pattern.findall(text)
        return len(matches) > 0

    def _has_trivial_deletion(self, text: str) -> bool:
        """Check if any cloze deletion is a trivial word."""
        matches = self._cloze_pattern.findall(text)
        for _, answer in matches:
            answer_stripped = answer.strip()
            # Check single-word answers for trivial words
            if len(answer_stripped.split()) == 1 and answer_stripped.lower() in TRIVIAL_WORDS:
                return True
        return False

    def _has_long_answer(self, text: str) -> bool:
        """Check if any cloze answer exceeds the maximum word count."""
        matches = self._cloze_pattern.findall(text)
        for _, answer in matches:
            word_count = len(answer.strip().split())
            if word_count > GeneratedClozeCard.MAX_ANSWER_WORDS:
                return True
        return False

    def _has_trivia_deletion(self, text: str) -> bool:
        """Check if any cloze deletion contains research trivia."""
        matches = self._cloze_pattern.findall(text)
        for _, answer in matches:
            answer_stripped = answer.strip()
            for pattern in TRIVIA_PATTERNS:
                if pattern.search(answer_stripped):
                    return True
            if answer_stripped.lower() in JOURNAL_NAMES:
                return True
        return False
