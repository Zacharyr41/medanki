from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from medanki.generation.service import (
    GenerationConfig,
    GenerationResult,
    GenerationService,
    GenerationStats,
)
from medanki.models.cards import ClozeCard, VignetteCard, VignetteOption
from medanki.services.protocols import Chunk, ChunkType, Document, DocumentType

if TYPE_CHECKING:
    pass


def make_chunk(content: str = "Test content", chunk_type: ChunkType | None = None) -> Chunk:
    return Chunk(
        id=uuid4(),
        document_id=uuid4(),
        content=content,
        chunk_type=chunk_type,
        start_offset=0,
        end_offset=len(content),
        metadata={},
    )


def make_cloze_card(chunk: Chunk, topic_id: str | None = None) -> ClozeCard:
    return ClozeCard(
        text="The {{c1::mitochondria}} is the powerhouse of the cell.",
        source_chunk_id=chunk.id,
        topic_id=topic_id,
    )


def make_vignette_card(chunk: Chunk, topic_id: str | None = None) -> VignetteCard:
    return VignetteCard(
        stem="A 45-year-old male presents with chest pain.",
        question="What is the most likely diagnosis?",
        options=[
            VignetteOption(letter="A", text="MI"),
            VignetteOption(letter="B", text="PE"),
            VignetteOption(letter="C", text="Dissection"),
            VignetteOption(letter="D", text="Pericarditis"),
            VignetteOption(letter="E", text="GERD"),
        ],
        answer="A",
        explanation="Classic MI presentation.",
        source_chunk_id=chunk.id,
        topic_id=topic_id,
    )


class TestOrchestration:
    @pytest.fixture
    def mock_cloze_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_vignette_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_validator(self) -> MagicMock:
        validator = MagicMock()
        validator.validate = AsyncMock(return_value=(True, []))
        return validator

    @pytest.fixture
    def mock_deduplicator(self) -> MagicMock:
        dedup = MagicMock()
        dedup.deduplicate = MagicMock(side_effect=lambda cards: cards)
        return dedup

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
        classifier = MagicMock()
        classifier.classify_chunk = AsyncMock(return_value=ChunkType.CONCEPT)
        return classifier

    @pytest.fixture
    def service(
        self,
        mock_cloze_generator: MagicMock,
        mock_vignette_generator: MagicMock,
        mock_validator: MagicMock,
        mock_deduplicator: MagicMock,
        mock_classifier: MagicMock,
    ) -> GenerationService:
        return GenerationService(
            cloze_generator=mock_cloze_generator,
            vignette_generator=mock_vignette_generator,
            validator=mock_validator,
            deduplicator=mock_deduplicator,
            classifier=mock_classifier,
        )

    @pytest.mark.asyncio
    async def test_generate_cards_from_chunk(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
        mock_vignette_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        cloze = make_cloze_card(chunk)
        vignette = make_vignette_card(chunk)

        mock_cloze_generator.generate.return_value = [cloze]
        mock_vignette_generator.generate.return_value = [vignette]

        result = await service.generate_cards([chunk])

        assert isinstance(result, GenerationResult)
        assert cloze in result.cards
        assert vignette in result.cards

    @pytest.mark.asyncio
    async def test_respects_card_type_config(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
        mock_vignette_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        cloze = make_cloze_card(chunk)
        mock_cloze_generator.generate.return_value = [cloze]
        mock_vignette_generator.generate.return_value = [make_vignette_card(chunk)]

        config = GenerationConfig(enable_vignettes=False)
        result = await service.generate_cards([chunk], config=config)

        mock_vignette_generator.generate.assert_not_called()
        assert all(isinstance(c, ClozeCard) for c in result.cards)

    @pytest.mark.asyncio
    async def test_respects_count_limits(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        config = GenerationConfig(max_cloze_per_chunk=2, max_vignette_per_chunk=1)

        await service.generate_cards([chunk], config=config)

        call_kwargs = mock_cloze_generator.generate.call_args
        assert call_kwargs.kwargs.get("num_cards") == 2 or call_kwargs[1].get("num_cards") == 2

    @pytest.mark.asyncio
    async def test_validates_all_cards(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
        mock_validator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        cards = [make_cloze_card(chunk) for _ in range(3)]
        mock_cloze_generator.generate.return_value = cards

        await service.generate_cards([chunk])

        assert mock_validator.validate.call_count >= len(cards)

    @pytest.mark.asyncio
    async def test_deduplicates_cards(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
        mock_deduplicator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        cards = [make_cloze_card(chunk) for _ in range(3)]
        mock_cloze_generator.generate.return_value = cards

        await service.generate_cards([chunk])

        mock_deduplicator.deduplicate.assert_called_once()


class TestPipeline:
    @pytest.fixture
    def mock_cloze_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_vignette_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_validator(self) -> MagicMock:
        validator = MagicMock()
        validator.validate = AsyncMock(return_value=(True, []))
        return validator

    @pytest.fixture
    def mock_deduplicator(self) -> MagicMock:
        dedup = MagicMock()
        dedup.deduplicate = MagicMock(side_effect=lambda cards: cards)
        return dedup

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
        classifier = MagicMock()
        classifier.classify_chunk = AsyncMock(return_value=ChunkType.CONCEPT)
        return classifier

    @pytest.fixture
    def service(
        self,
        mock_cloze_generator: MagicMock,
        mock_vignette_generator: MagicMock,
        mock_validator: MagicMock,
        mock_deduplicator: MagicMock,
        mock_classifier: MagicMock,
    ) -> GenerationService:
        return GenerationService(
            cloze_generator=mock_cloze_generator,
            vignette_generator=mock_vignette_generator,
            validator=mock_validator,
            deduplicator=mock_deduplicator,
            classifier=mock_classifier,
        )

    @pytest.mark.asyncio
    async def test_classify_then_generate(
        self,
        service: GenerationService,
        mock_classifier: MagicMock,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        mock_classifier.classify_chunk.return_value = ChunkType.CLINICAL_VIGNETTE

        await service.generate_cards([chunk])

        mock_classifier.classify_chunk.assert_called_once_with(chunk)

    @pytest.mark.asyncio
    async def test_uses_topic_for_generation(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        topic_id = "cardiology.arrythmia"

        await service.generate_cards([chunk], topic_id=topic_id)

        call_kwargs = mock_cloze_generator.generate.call_args
        assert call_kwargs.kwargs.get("topic_id") == topic_id or topic_id in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_tracks_provenance(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        card = make_cloze_card(chunk)
        mock_cloze_generator.generate.return_value = [card]

        result = await service.generate_cards([chunk])

        for c in result.cards:
            assert c.source_chunk_id == chunk.id


class TestBatchProcessing:
    @pytest.fixture
    def mock_cloze_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_vignette_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_validator(self) -> MagicMock:
        validator = MagicMock()
        validator.validate = AsyncMock(return_value=(True, []))
        return validator

    @pytest.fixture
    def mock_deduplicator(self) -> MagicMock:
        dedup = MagicMock()
        dedup.deduplicate = MagicMock(side_effect=lambda cards: cards)
        return dedup

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
        classifier = MagicMock()
        classifier.classify_chunk = AsyncMock(return_value=ChunkType.CONCEPT)
        return classifier

    @pytest.fixture
    def service(
        self,
        mock_cloze_generator: MagicMock,
        mock_vignette_generator: MagicMock,
        mock_validator: MagicMock,
        mock_deduplicator: MagicMock,
        mock_classifier: MagicMock,
    ) -> GenerationService:
        return GenerationService(
            cloze_generator=mock_cloze_generator,
            vignette_generator=mock_vignette_generator,
            validator=mock_validator,
            deduplicator=mock_deduplicator,
            classifier=mock_classifier,
        )

    @pytest.mark.asyncio
    async def test_generate_from_document(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        from pathlib import Path

        doc = Document(
            id=uuid4(),
            path=Path("/test/doc.pdf"),
            content="Full document content",
            document_type=DocumentType.PDF,
            metadata={},
        )
        chunks = [make_chunk(f"Chunk {i}") for i in range(3)]

        for chunk in chunks:
            mock_cloze_generator.generate.return_value = [make_cloze_card(chunk)]

        result = await service.generate_from_document(doc, chunks)

        assert isinstance(result, GenerationResult)

    @pytest.mark.asyncio
    async def test_generate_from_multiple_docs(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        from pathlib import Path

        docs = [
            Document(
                id=uuid4(),
                path=Path(f"/test/doc{i}.pdf"),
                content=f"Content {i}",
                document_type=DocumentType.PDF,
                metadata={},
            )
            for i in range(2)
        ]
        chunks_by_doc = {doc.id: [make_chunk(f"Chunk for {doc.id}")] for doc in docs}

        result = await service.generate_from_documents(docs, chunks_by_doc)

        assert isinstance(result, GenerationResult)

    @pytest.mark.asyncio
    async def test_progress_callback(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunks = [make_chunk(f"Chunk {i}") for i in range(3)]
        progress_calls: list[tuple[int, int]] = []

        def on_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        await service.generate_cards(chunks, on_progress=on_progress)

        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == progress_calls[-1][1]

    @pytest.mark.asyncio
    async def test_handles_generation_failure(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunks = [make_chunk(f"Chunk {i}") for i in range(3)]

        async def generate_with_failure(*args, **kwargs):
            content = kwargs.get("content", args[0] if args else "")
            if "Chunk 1" in str(content):
                raise Exception("Generation failed for chunk 1")
            chunk_id = kwargs.get("source_chunk_id", uuid4())
            return [
                ClozeCard(
                    text="The {{c1::answer}} is correct.",
                    source_chunk_id=chunk_id,
                )
            ]

        mock_cloze_generator.generate.side_effect = generate_with_failure

        result = await service.generate_cards(chunks)

        assert len(result.errors) >= 1
        assert len(result.cards) >= 0


class TestQualityControl:
    @pytest.fixture
    def mock_cloze_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_vignette_generator(self) -> MagicMock:
        gen = MagicMock()
        gen.generate = AsyncMock(return_value=[])
        return gen

    @pytest.fixture
    def mock_validator(self) -> MagicMock:
        validator = MagicMock()
        validator.validate = AsyncMock(return_value=(True, []))
        return validator

    @pytest.fixture
    def mock_deduplicator(self) -> MagicMock:
        dedup = MagicMock()
        dedup.deduplicate = MagicMock(side_effect=lambda cards: cards)
        return dedup

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
        classifier = MagicMock()
        classifier.classify_chunk = AsyncMock(return_value=ChunkType.CONCEPT)
        return classifier

    @pytest.fixture
    def service(
        self,
        mock_cloze_generator: MagicMock,
        mock_vignette_generator: MagicMock,
        mock_validator: MagicMock,
        mock_deduplicator: MagicMock,
        mock_classifier: MagicMock,
    ) -> GenerationService:
        return GenerationService(
            cloze_generator=mock_cloze_generator,
            vignette_generator=mock_vignette_generator,
            validator=mock_validator,
            deduplicator=mock_deduplicator,
            classifier=mock_classifier,
        )

    @pytest.mark.asyncio
    async def test_filters_low_confidence(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
        mock_validator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        good_card = make_cloze_card(chunk)
        bad_card = make_cloze_card(chunk)

        mock_cloze_generator.generate.return_value = [good_card, bad_card]

        async def validate_card(card, source_content=None):
            if card is bad_card:
                return (False, ["Low confidence"])
            return (True, [])

        mock_validator.validate.side_effect = validate_card

        result = await service.generate_cards([chunk])

        assert good_card in result.cards
        assert bad_card not in result.cards

    @pytest.mark.asyncio
    async def test_hallucination_check_enabled(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
        mock_validator: MagicMock,
    ) -> None:
        chunk = make_chunk("The heart pumps blood.")
        card = make_cloze_card(chunk)
        mock_cloze_generator.generate.return_value = [card]

        config = GenerationConfig(check_hallucination=True)
        await service.generate_cards([chunk], config=config)

        call_args = mock_validator.validate.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_returns_generation_stats(
        self,
        service: GenerationService,
        mock_cloze_generator: MagicMock,
    ) -> None:
        chunk = make_chunk()
        mock_cloze_generator.generate.return_value = [make_cloze_card(chunk)]

        result = await service.generate_cards([chunk])

        assert isinstance(result.stats, GenerationStats)
        assert result.stats.total_cards >= 0
        assert result.stats.duration_seconds >= 0
