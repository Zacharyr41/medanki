from unittest.mock import AsyncMock, MagicMock

import pytest

from medanki.generation.deduplicator import (
    DeduplicationResult,
    Deduplicator,
    DuplicateStatus,
)
from medanki.generation.validator import ClozeCard


class TestExactDuplicateDetection:
    def test_detects_exact_duplicate(self):
        deduplicator = Deduplicator()
        card1 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="The mitochondria is the powerhouse of the cell."
        )
        card2 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="The mitochondria is the powerhouse of the cell."
        )

        result = deduplicator.check_duplicate(card1, [card2])

        assert result.is_duplicate is True
        assert result.status == DuplicateStatus.EXACT

    def test_content_hash_matching(self):
        deduplicator = Deduplicator()
        card1 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source A"
        )
        card2 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source B"
        )

        hash1 = deduplicator.compute_content_hash(card1)
        hash2 = deduplicator.compute_content_hash(card2)

        assert hash1 == hash2


class TestSemanticDuplicateDetection:
    @pytest.fixture
    def mock_embedding_client(self):
        client = MagicMock()
        client.embed = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_detects_semantic_duplicate(self, mock_embedding_client):
        mock_embedding_client.embed.side_effect = [
            [0.9, 0.1, 0.05],
            [0.91, 0.09, 0.04],
        ]

        deduplicator = Deduplicator(embedding_client=mock_embedding_client)
        card1 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source A"
        )
        card2 = ClozeCard(
            text="The {{c1::mitochondrion}} is the cell's power generator.",
            source_chunk="Source B"
        )

        result = await deduplicator.check_semantic_duplicate(card1, [card2])

        assert result.is_duplicate is True
        assert result.status == DuplicateStatus.SEMANTIC

    @pytest.mark.asyncio
    async def test_similarity_threshold(self, mock_embedding_client):
        mock_embedding_client.embed.side_effect = [
            [0.9, 0.1, 0.05],
            [0.92, 0.08, 0.03],
        ]

        deduplicator = Deduplicator(
            embedding_client=mock_embedding_client,
            similarity_threshold=0.9
        )
        card1 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source A"
        )
        card2 = ClozeCard(
            text="The {{c1::mitochondria}} produces ATP for the cell.",
            source_chunk="Source B"
        )

        result = await deduplicator.check_semantic_duplicate(card1, [card2])

        assert result.similarity_score >= 0.9
        assert result.is_duplicate is True

    @pytest.mark.asyncio
    async def test_different_cards_pass(self, mock_embedding_client):
        mock_embedding_client.embed.side_effect = [
            [0.9, 0.1, 0.0],
            [0.1, 0.8, 0.1],
        ]

        deduplicator = Deduplicator(
            embedding_client=mock_embedding_client,
            similarity_threshold=0.9
        )
        card1 = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source A"
        )
        card2 = ClozeCard(
            text="{{c1::Hypertension}} is defined as BP > 130/80.",
            source_chunk="Source B"
        )

        result = await deduplicator.check_semantic_duplicate(card1, [card2])

        assert result.is_duplicate is False


class TestCrossSessionDeduplication:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.get_existing_cards = MagicMock()
        db.get_card_embeddings = MagicMock()
        return db

    @pytest.fixture
    def mock_embedding_client(self):
        client = MagicMock()
        client.embed = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_checks_existing_cards(self, mock_db, mock_embedding_client):
        existing_card = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source A"
        )
        mock_db.get_existing_cards.return_value = [existing_card]

        deduplicator = Deduplicator(
            embedding_client=mock_embedding_client,
            database=mock_db
        )
        new_card = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source B"
        )

        result = await deduplicator.check_against_existing(new_card)

        assert result.is_duplicate is True
        mock_db.get_existing_cards.assert_called_once()

    def test_marks_vs_removes(self, mock_db, mock_embedding_client):
        deduplicator = Deduplicator(
            embedding_client=mock_embedding_client,
            database=mock_db
        )
        card = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="Source A"
        )
        duplicate_result = DeduplicationResult(
            is_duplicate=True,
            status=DuplicateStatus.EXACT,
            similarity_score=1.0
        )

        marked = deduplicator.handle_duplicate(card, duplicate_result, action="mark")
        assert marked.is_marked_duplicate is True
        assert marked.card is not None

        removed = deduplicator.handle_duplicate(card, duplicate_result, action="remove")
        assert removed.card is None
