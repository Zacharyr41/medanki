import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Any

from medanki.models.cards import ClozeCard, VignetteCard


class DuplicateStatus(Enum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    UNIQUE = "unique"


@dataclass
class DeduplicationResult:
    is_duplicate: bool
    status: DuplicateStatus
    similarity_score: float = 0.0
    duplicate_of: ClozeCard | VignetteCard | None = None


@dataclass
class DuplicateHandleResult:
    card: ClozeCard | VignetteCard | None
    is_marked_duplicate: bool = False


class IEmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class IDatabase(Protocol):
    def get_existing_cards(self) -> list[ClozeCard | VignetteCard]: ...
    def get_card_embeddings(self, cards: list[ClozeCard | VignetteCard]) -> dict[Any, list[float]]: ...


class Deduplicator:
    def __init__(
        self,
        embedding_client: IEmbeddingClient | None = None,
        database: IDatabase | None = None,
        similarity_threshold: float = 0.9
    ):
        self.embedding_client = embedding_client
        self.database = database
        self.similarity_threshold = similarity_threshold

    def compute_content_hash(self, card: ClozeCard | VignetteCard) -> str:
        if isinstance(card, ClozeCard):
            content = card.text
        else:
            content = card.stem + "".join(opt.text for opt in card.options) + card.answer
        return hashlib.sha256(content.encode()).hexdigest()

    def check_duplicate(
        self,
        card: ClozeCard | VignetteCard,
        existing_cards: list[ClozeCard | VignetteCard]
    ) -> DeduplicationResult:
        card_hash = self.compute_content_hash(card)

        for existing in existing_cards:
            if self.compute_content_hash(existing) == card_hash:
                return DeduplicationResult(
                    is_duplicate=True,
                    status=DuplicateStatus.EXACT,
                    similarity_score=1.0,
                    duplicate_of=existing
                )

        return DeduplicationResult(
            is_duplicate=False,
            status=DuplicateStatus.UNIQUE,
            similarity_score=0.0
        )

    async def check_semantic_duplicate(
        self,
        card: ClozeCard | VignetteCard,
        existing_cards: list[ClozeCard | VignetteCard]
    ) -> DeduplicationResult:
        if not self.embedding_client:
            return DeduplicationResult(
                is_duplicate=False,
                status=DuplicateStatus.UNIQUE,
                similarity_score=0.0
            )

        card_text = card.text if isinstance(card, ClozeCard) else card.stem
        card_embedding = await self.embedding_client.embed(card_text)

        max_similarity = 0.0
        most_similar_card = None

        for existing in existing_cards:
            existing_text = existing.text if isinstance(existing, ClozeCard) else existing.stem
            existing_embedding = await self.embedding_client.embed(existing_text)

            similarity = self._cosine_similarity(card_embedding, existing_embedding)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_card = existing

        if max_similarity >= self.similarity_threshold:
            return DeduplicationResult(
                is_duplicate=True,
                status=DuplicateStatus.SEMANTIC,
                similarity_score=max_similarity,
                duplicate_of=most_similar_card
            )

        return DeduplicationResult(
            is_duplicate=False,
            status=DuplicateStatus.UNIQUE,
            similarity_score=max_similarity
        )

    async def check_against_existing(
        self,
        card: ClozeCard | VignetteCard
    ) -> DeduplicationResult:
        if not self.database:
            return DeduplicationResult(
                is_duplicate=False,
                status=DuplicateStatus.UNIQUE,
                similarity_score=0.0
            )

        existing_cards = self.database.get_existing_cards()

        exact_result = self.check_duplicate(card, existing_cards)
        if exact_result.is_duplicate:
            return exact_result

        if self.embedding_client:
            return await self.check_semantic_duplicate(card, existing_cards)

        return DeduplicationResult(
            is_duplicate=False,
            status=DuplicateStatus.UNIQUE,
            similarity_score=0.0
        )

    def handle_duplicate(
        self,
        card: ClozeCard | VignetteCard,
        result: DeduplicationResult,
        action: str = "mark"
    ) -> DuplicateHandleResult:
        if not result.is_duplicate:
            return DuplicateHandleResult(card=card, is_marked_duplicate=False)

        if action == "remove":
            return DuplicateHandleResult(card=None, is_marked_duplicate=False)

        return DuplicateHandleResult(card=card, is_marked_duplicate=True)

    def deduplicate(self, cards: list[ClozeCard | VignetteCard]) -> list[ClozeCard | VignetteCard]:
        seen_hashes: set[str] = set()
        unique_cards: list[ClozeCard | VignetteCard] = []

        for card in cards:
            card_hash = self.compute_content_hash(card)
            if card_hash not in seen_hashes:
                seen_hashes.add(card_hash)
                unique_cards.append(card)

        return unique_cards

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
