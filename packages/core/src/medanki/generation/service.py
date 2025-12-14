from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable
from uuid import UUID

from medanki.models.cards import ClozeCard, VignetteCard

if TYPE_CHECKING:
    from collections.abc import Sequence

    from medanki.services.protocols import Chunk, Document


@runtime_checkable
class IClozeGenerator(Protocol):
    async def generate(
        self,
        content: str,
        source_chunk_id: UUID,
        topic_id: str | None = None,
        num_cards: int = 3,
    ) -> list[ClozeCard]: ...


@runtime_checkable
class IVignetteGenerator(Protocol):
    async def generate(
        self,
        content: str,
        source_chunk_id: UUID,
        topic_id: str | None = None,
        num_cards: int = 1,
    ) -> list[VignetteCard]: ...


@runtime_checkable
class ICardValidator(Protocol):
    async def validate(
        self,
        card: ClozeCard | VignetteCard,
        source_content: str | None = None,
    ) -> tuple[bool, list[str]]: ...


@runtime_checkable
class IDeduplicator(Protocol):
    def deduplicate(
        self,
        cards: list[ClozeCard | VignetteCard],
    ) -> list[ClozeCard | VignetteCard]: ...


@runtime_checkable
class IClassifier(Protocol):
    async def classify_chunk(self, chunk: Chunk) -> str: ...


@dataclass
class GenerationConfig:
    enable_cloze: bool = True
    enable_vignettes: bool = True
    max_cloze_per_chunk: int = 3
    max_vignette_per_chunk: int = 1
    check_hallucination: bool = False
    min_confidence: float = 0.5


@dataclass
class GenerationStats:
    total_cards: int = 0
    cloze_count: int = 0
    vignette_count: int = 0
    duration_seconds: float = 0.0
    chunks_processed: int = 0
    chunks_failed: int = 0


@dataclass
class GenerationError:
    chunk_id: UUID
    error_message: str


@dataclass
class GenerationResult:
    cards: list[ClozeCard | VignetteCard] = field(default_factory=list)
    stats: GenerationStats = field(default_factory=GenerationStats)
    errors: list[GenerationError] = field(default_factory=list)


ProgressCallback = Callable[[int, int], None]


@dataclass
class GenerationService:
    cloze_generator: IClozeGenerator
    vignette_generator: IVignetteGenerator
    validator: ICardValidator
    deduplicator: IDeduplicator
    classifier: IClassifier

    async def generate_cards(
        self,
        chunks: Sequence[Chunk],
        config: GenerationConfig | None = None,
        topic_id: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        if config is None:
            config = GenerationConfig()

        start_time = time.monotonic()
        all_cards: list[ClozeCard | VignetteCard] = []
        errors: list[GenerationError] = []
        chunks_processed = 0
        chunks_failed = 0
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            try:
                await self.classifier.classify_chunk(chunk)

                chunk_cards: list[ClozeCard | VignetteCard] = []

                if config.enable_cloze:
                    cloze_cards = await self.cloze_generator.generate(
                        content=chunk.content,
                        source_chunk_id=chunk.id,
                        topic_id=topic_id,
                        num_cards=config.max_cloze_per_chunk,
                    )
                    chunk_cards.extend(cloze_cards)

                if config.enable_vignettes:
                    vignette_cards = await self.vignette_generator.generate(
                        content=chunk.content,
                        source_chunk_id=chunk.id,
                        topic_id=topic_id,
                        num_cards=config.max_vignette_per_chunk,
                    )
                    chunk_cards.extend(vignette_cards)

                validated_cards: list[ClozeCard | VignetteCard] = []
                for card in chunk_cards:
                    source_content = chunk.content if config.check_hallucination else None
                    is_valid, _ = await self.validator.validate(card, source_content)
                    if is_valid:
                        validated_cards.append(card)

                all_cards.extend(validated_cards)
                chunks_processed += 1

            except Exception as e:
                errors.append(GenerationError(chunk_id=chunk.id, error_message=str(e)))
                chunks_failed += 1

            if on_progress:
                on_progress(i + 1, total_chunks)

        deduplicated_cards = self.deduplicator.deduplicate(all_cards)

        duration = time.monotonic() - start_time
        cloze_count = sum(1 for c in deduplicated_cards if isinstance(c, ClozeCard))
        vignette_count = sum(1 for c in deduplicated_cards if isinstance(c, VignetteCard))

        stats = GenerationStats(
            total_cards=len(deduplicated_cards),
            cloze_count=cloze_count,
            vignette_count=vignette_count,
            duration_seconds=duration,
            chunks_processed=chunks_processed,
            chunks_failed=chunks_failed,
        )

        return GenerationResult(cards=deduplicated_cards, stats=stats, errors=errors)

    async def generate_from_document(
        self,
        document: Document,
        chunks: Sequence[Chunk],
        config: GenerationConfig | None = None,
        topic_id: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        return await self.generate_cards(
            chunks=chunks,
            config=config,
            topic_id=topic_id,
            on_progress=on_progress,
        )

    async def generate_from_documents(
        self,
        documents: Sequence[Document],
        chunks_by_doc: dict[UUID, Sequence[Chunk]],
        config: GenerationConfig | None = None,
        topic_id: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        all_chunks: list[Chunk] = []
        for doc in documents:
            doc_chunks = chunks_by_doc.get(doc.id, [])
            all_chunks.extend(doc_chunks)

        return await self.generate_cards(
            chunks=all_chunks,
            config=config,
            topic_id=topic_id,
            on_progress=on_progress,
        )
