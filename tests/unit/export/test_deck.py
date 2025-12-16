"""Tests for Anki deck building."""

import genanki

from packages.core.src.medanki.export.deck import DeckBuilder
from tests.conftest import ClozeCard, VignetteCard


class TestDeckBuilder:
    def test_creates_deck(self):
        """genanki.Deck created."""
        builder = DeckBuilder("Test Deck")
        deck = builder.build()
        assert isinstance(deck, genanki.Deck)
        assert deck.name == "Test Deck"

    def test_deck_id_stable(self):
        """ID based on name hash - same name = same ID."""
        builder1 = DeckBuilder("My Medical Deck")
        builder2 = DeckBuilder("My Medical Deck")
        assert builder1.deck_id == builder2.deck_id

    def test_different_names_different_ids(self):
        builder1 = DeckBuilder("Deck A")
        builder2 = DeckBuilder("Deck B")
        assert builder1.deck_id != builder2.deck_id

    def test_adds_cloze_notes(self):
        """ClozeCard -> genanki.Note."""
        builder = DeckBuilder("Test Deck")
        card = ClozeCard(
            id="test_001",
            text="The {{c1::heart}} pumps blood",
            extra="Additional info",
            source_chunk_id="chunk_001",
            tags=["cardiology"],
        )
        builder.add_cloze_card(card)
        deck = builder.build()
        assert len(deck.notes) == 1

    def test_adds_vignette_notes(self):
        """VignetteCard -> genanki.Note."""
        builder = DeckBuilder("Test Deck")
        card = VignetteCard(
            id="test_002",
            front="A 45-year-old presents with chest pain...",
            answer="Myocardial Infarction",
            explanation="Classic presentation of MI",
            distinguishing_feature="ST elevation",
            source_chunk_id="chunk_002",
            tags=["cardiology"],
        )
        builder.add_vignette_card(card)
        deck = builder.build()
        assert len(deck.notes) == 1

    def test_guid_from_content(self):
        """Stable GUID for updates - same content = same GUID."""
        builder = DeckBuilder("Test Deck")
        card1 = ClozeCard(
            id="test_001", text="The {{c1::heart}} pumps blood", source_chunk_id="chunk_001"
        )
        card2 = ClozeCard(
            id="test_002", text="The {{c1::heart}} pumps blood", source_chunk_id="chunk_001"
        )
        guid1 = builder.generate_guid(card1)
        guid2 = builder.generate_guid(card2)
        assert guid1 == guid2

    def test_different_content_different_guid(self):
        builder = DeckBuilder("Test Deck")
        card1 = ClozeCard(
            id="test_001", text="The {{c1::heart}} pumps blood", source_chunk_id="chunk_001"
        )
        card2 = ClozeCard(
            id="test_002", text="The {{c1::brain}} controls the body", source_chunk_id="chunk_001"
        )
        guid1 = builder.generate_guid(card1)
        guid2 = builder.generate_guid(card2)
        assert guid1 != guid2

    def test_hierarchical_deck_names(self):
        """'MedAnki::MCAT::Biology'"""
        builder = DeckBuilder.from_hierarchy(["MedAnki", "MCAT", "Biology"])
        assert builder.name == "MedAnki::MCAT::Biology"

    def test_adds_multiple_cards(self):
        builder = DeckBuilder("Test Deck")
        for i in range(5):
            card = ClozeCard(
                id=f"test_{i:03d}",
                text=f"The {{{{c1::term{i}}}}} is important",
                source_chunk_id=f"chunk_{i:03d}",
            )
            builder.add_cloze_card(card)
        deck = builder.build()
        assert len(deck.notes) == 5
