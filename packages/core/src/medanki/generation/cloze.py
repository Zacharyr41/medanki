"""Cloze card generation service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID, uuid4

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
TRIVIAL_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "of", "to", "and", "or", "in", "on", "at", "for", "with",
    "it", "its", "this", "that", "these", "those",
})


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
        classified_chunk: Any,
        count: int = 3,
    ) -> list[GeneratedClozeCard]:
        """Generate cloze cards from a classified chunk.

        Args:
            classified_chunk: A chunk with text and topic classifications.
            count: Maximum number of cards to generate.

        Returns:
            List of validated GeneratedClozeCard objects.

        Raises:
            Exception: If the LLM client fails.
        """
        # Extract text and tags from the classified chunk
        text = getattr(classified_chunk, "text", "")
        tags = getattr(classified_chunk, "tags", [])
        chunk_id = getattr(classified_chunk, "id", uuid4())

        # Call LLM to generate cards
        raw_cards = await self._llm_client.generate_cloze_cards(
            text=text,
            count=count,
            tags=tags,
        )

        # Process and validate cards
        valid_cards: list[GeneratedClozeCard] = []
        for raw_card in raw_cards:
            card_text = raw_card.get("text", "")
            card_tags = raw_card.get("tags", [])

            # Skip cards without valid cloze syntax
            if not self._has_valid_cloze_syntax(card_text):
                continue

            # Skip cards with trivial deletions
            if self._has_trivial_deletion(card_text):
                continue

            # Skip cards with answers that are too long
            if self._has_long_answer(card_text):
                continue

            card = GeneratedClozeCard(
                text=card_text,
                source_chunk_id=chunk_id,
                tags=card_tags or tags,
            )

            if card.is_valid():
                valid_cards.append(card)

        # Respect the count parameter
        return valid_cards[:count]

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
