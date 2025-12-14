"""Integration tests for the export pipeline.

Tests deck building, APKG export, and tag formatting.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from medanki.export.apkg import APKGExporter
from medanki.export.deck import DeckBuilder
from medanki.export.tags import TagBuilder


# ============================================================================
# Test Data Classes
# ============================================================================

class MockClozeCard:
    """Mock cloze card for testing."""

    def __init__(
        self,
        text: str,
        extra: str = "",
        source_chunk_id: str = "",
        tags: list[str] | None = None,
    ):
        self.text = text
        self.extra = extra
        self.source_chunk_id = source_chunk_id or str(uuid4())
        self.tags = tags or []


class MockVignetteCard:
    """Mock vignette card for testing."""

    def __init__(
        self,
        front: str,
        answer: str,
        explanation: str,
        distinguishing_feature: str | None = None,
        source_chunk_id: str = "",
        tags: list[str] | None = None,
    ):
        self.front = front
        self.answer = answer
        self.explanation = explanation
        self.distinguishing_feature = distinguishing_feature
        self.source_chunk_id = source_chunk_id or str(uuid4())
        self.tags = tags or []


# ============================================================================
# Deck Building Tests
# ============================================================================

@pytest.mark.integration
class TestDeckBuilding:
    """Test deck building from cards."""

    def test_build_deck_from_cloze_cards(self) -> None:
        """Test building a deck from cloze cards."""
        builder = DeckBuilder(name="MedAnki::Cardiology")

        cards = [
            MockClozeCard(
                text="The cardiac cycle consists of {{c1::systole}} and {{c2::diastole}}.",
                extra="Source: Cardiology lecture",
                tags=["cardiology", "physiology"],
            ),
            MockClozeCard(
                text="{{c1::Lisinopril}} is an ACE inhibitor.",
                extra="Source: Pharmacology notes",
                tags=["pharmacology"],
            ),
        ]

        for card in cards:
            builder.add_cloze_card(card)

        deck = builder.build()

        # Verify deck structure
        assert deck is not None
        assert deck.name == "MedAnki::Cardiology"
        assert len(deck.notes) == 2

    def test_build_deck_from_vignette_cards(self) -> None:
        """Test building a deck from vignette cards."""
        builder = DeckBuilder(name="MedAnki::Vignettes")

        cards = [
            MockVignetteCard(
                front="A 55-year-old male presents with crushing chest pain. What is the diagnosis?",
                answer="A",
                explanation="ST elevation indicates STEMI.",
                distinguishing_feature="Crushing substernal chest pain",
                tags=["cardiology", "emergency"],
            ),
        ]

        for card in cards:
            builder.add_vignette_card(card)

        deck = builder.build()

        assert deck is not None
        assert len(deck.notes) == 1

    def test_build_deck_with_hierarchy(self) -> None:
        """Test building a deck with hierarchical name."""
        builder = DeckBuilder.from_hierarchy(["MedAnki", "USMLE", "Cardiology"])

        deck = builder.build()

        assert deck.name == "MedAnki::USMLE::Cardiology"

    def test_deck_id_is_deterministic(self) -> None:
        """Test that deck ID is consistent for same name."""
        builder1 = DeckBuilder(name="MedAnki::Cardiology")
        builder2 = DeckBuilder(name="MedAnki::Cardiology")

        assert builder1.deck_id == builder2.deck_id

    def test_deck_id_differs_for_different_names(self) -> None:
        """Test that different names produce different deck IDs."""
        builder1 = DeckBuilder(name="MedAnki::Cardiology")
        builder2 = DeckBuilder(name="MedAnki::Pharmacology")

        assert builder1.deck_id != builder2.deck_id

    def test_guid_is_deterministic(self) -> None:
        """Test that card GUID is deterministic for same content."""
        builder = DeckBuilder(name="Test")

        card = MockClozeCard(text="Test {{c1::content}}")

        guid1 = builder.generate_guid(card)
        guid2 = builder.generate_guid(card)

        assert guid1 == guid2


# ============================================================================
# APKG Export Tests
# ============================================================================

@pytest.mark.integration
class TestAPKGExport:
    """Test APKG file export."""

    def test_export_apkg_file(self, temp_output_dir: Path) -> None:
        """Test exporting a deck to APKG file."""
        builder = DeckBuilder(name="MedAnki::Test")

        # Add some cards
        builder.add_cloze_card(
            MockClozeCard(
                text="The heart has {{c1::four}} chambers.",
                tags=["cardiology"],
            )
        )

        deck = builder.build()

        # Export to APKG
        exporter = APKGExporter()
        output_path = str(temp_output_dir / "test_deck.apkg")

        exporter.export(deck, output_path)

        # Verify file was created
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0

    def test_apkg_is_valid_zip(self, temp_output_dir: Path) -> None:
        """Test that APKG file is a valid ZIP archive."""
        builder = DeckBuilder(name="MedAnki::Validation")

        builder.add_cloze_card(
            MockClozeCard(text="Test {{c1::card}}")
        )

        deck = builder.build()
        exporter = APKGExporter()
        output_path = str(temp_output_dir / "validation_test.apkg")

        exporter.export(deck, output_path)

        # APKG files are ZIP archives
        assert zipfile.is_zipfile(output_path)

        # Should contain collection.anki2 database
        with zipfile.ZipFile(output_path, 'r') as zf:
            names = zf.namelist()
            assert "collection.anki2" in names

    def test_export_multiple_decks(self, temp_output_dir: Path) -> None:
        """Test exporting multiple decks to single APKG."""
        deck1_builder = DeckBuilder(name="MedAnki::Cardiology")
        deck1_builder.add_cloze_card(
            MockClozeCard(text="Cardiology {{c1::card}}")
        )
        deck1 = deck1_builder.build()

        deck2_builder = DeckBuilder(name="MedAnki::Pharmacology")
        deck2_builder.add_cloze_card(
            MockClozeCard(text="Pharmacology {{c1::card}}")
        )
        deck2 = deck2_builder.build()

        exporter = APKGExporter()
        output_path = str(temp_output_dir / "multi_deck.apkg")

        exporter.export_multiple([deck1, deck2], output_path)

        assert Path(output_path).exists()

    def test_export_with_empty_deck(self, temp_output_dir: Path) -> None:
        """Test exporting an empty deck."""
        builder = DeckBuilder(name="MedAnki::Empty")
        deck = builder.build()

        exporter = APKGExporter()
        output_path = str(temp_output_dir / "empty_deck.apkg")

        exporter.export(deck, output_path)

        # Should still create a valid file
        assert Path(output_path).exists()


# ============================================================================
# Tag Building Tests
# ============================================================================

@pytest.mark.integration
class TestTagBuilding:
    """Test tag building and formatting."""

    def test_build_mcat_tag(self) -> None:
        """Test building MCAT-style tags."""
        builder = TagBuilder()

        tag = builder.build_mcat_tag("Foundational Concept 4 > Cardiovascular > Heart")

        assert tag.startswith("#MCAT::")
        assert "Foundational_Concept_4" in tag
        assert "Cardiovascular" in tag
        assert "Heart" in tag

    def test_build_usmle_tag(self) -> None:
        """Test building USMLE-style tags."""
        builder = TagBuilder()

        tag = builder.build_usmle_tag("Step1", "Cardiovascular", "Heart_Failure")

        assert tag.startswith("#AK_Step1_v12::")
        assert "Cardiovascular" in tag
        assert "Heart_Failure" in tag

    def test_build_source_tag(self) -> None:
        """Test building source attribution tags."""
        builder = TagBuilder()

        tag = builder.build_source_tag("Cardiology_Lecture_01")

        assert tag.startswith("#Source::MedAnki::")
        assert "Cardiology_Lecture_01" in tag

    def test_sanitize_removes_special_characters(self) -> None:
        """Test that sanitization handles special characters."""
        builder = TagBuilder()

        result = builder.sanitize("Heart's Function: Overview")

        # Should remove quotes and colons, replace spaces with underscores
        assert "'" not in result
        assert ":" not in result
        assert " " not in result
        assert "_" in result

    def test_build_hierarchical_tag(self) -> None:
        """Test building hierarchical tags."""
        builder = TagBuilder()

        tag = builder.build_hierarchical_tag(["MedAnki", "Cardiology", "CHF"])

        assert tag == "#MedAnki::Cardiology::CHF"

    def test_build_hierarchical_tag_empty(self) -> None:
        """Test hierarchical tag with empty list."""
        builder = TagBuilder()

        tag = builder.build_hierarchical_tag([])

        assert tag == ""


# ============================================================================
# Tag Correctness Tests (AnKing Format)
# ============================================================================

@pytest.mark.integration
class TestTagCorrectness:
    """Test that tags follow AnKing format conventions."""

    def test_tags_use_double_colon_separator(self) -> None:
        """Test that tags use :: as hierarchy separator."""
        builder = TagBuilder()

        mcat_tag = builder.build_mcat_tag("Category > Subcategory")
        usmle_tag = builder.build_usmle_tag("Step1", "Category", "Topic")

        assert "::" in mcat_tag
        assert "::" in usmle_tag

    def test_tags_start_with_hash(self) -> None:
        """Test that all tags start with #."""
        builder = TagBuilder()

        mcat_tag = builder.build_mcat_tag("Test")
        usmle_tag = builder.build_usmle_tag("Step1", "Test")
        source_tag = builder.build_source_tag("Test")

        assert mcat_tag.startswith("#")
        assert usmle_tag.startswith("#")
        assert source_tag.startswith("#")

    def test_tags_no_spaces(self) -> None:
        """Test that tags have no spaces (replaced with underscores)."""
        builder = TagBuilder()

        tag = builder.build_mcat_tag("Foundational Concept 4 > Heart Anatomy")

        assert " " not in tag

    def test_deck_has_correct_tags(self, temp_output_dir: Path) -> None:
        """Test that cards in exported deck have correct tags."""
        tag_builder = TagBuilder()
        deck_builder = DeckBuilder(name="MedAnki::Test")

        # Create card with proper tags
        mcat_tag = tag_builder.build_mcat_tag("FC4 > Cardiovascular")
        source_tag = tag_builder.build_source_tag("Test_Lecture")

        card = MockClozeCard(
            text="The heart has {{c1::four}} chambers.",
            tags=[mcat_tag, source_tag],
        )

        deck_builder.add_cloze_card(card)
        deck = deck_builder.build()

        # Verify tags were included
        assert len(deck.notes) == 1
        note = deck.notes[0]
        assert len(note.tags) == 2

        # Tags should be properly formatted
        for tag in note.tags:
            assert "::" in tag
            assert " " not in tag


# ============================================================================
# Full Export Pipeline Tests
# ============================================================================

@pytest.mark.integration
class TestFullExportPipeline:
    """Test the complete export pipeline."""

    def test_cards_to_apkg_full(self, temp_output_dir: Path) -> None:
        """Test full pipeline from cards to APKG file."""
        # Create cards
        tag_builder = TagBuilder()
        cards = [
            MockClozeCard(
                text="The cardiac cycle has {{c1::systole}} and {{c2::diastole}} phases.",
                extra="Lecture 1",
                tags=[
                    tag_builder.build_mcat_tag("FC4 > Cardiovascular"),
                    tag_builder.build_source_tag("Cardiology_Lecture"),
                ],
            ),
            MockClozeCard(
                text="{{c1::Lisinopril}} is an ACE inhibitor used for hypertension.",
                extra="Lecture 2",
                tags=[
                    tag_builder.build_usmle_tag("Step1", "Pharmacology", "Cardiovascular"),
                ],
            ),
            MockVignetteCard(
                front="A 60-year-old presents with chest pain. What is the diagnosis?",
                answer="STEMI",
                explanation="ST elevation with troponin rise.",
                tags=[
                    tag_builder.build_mcat_tag("FC4 > Cardiology"),
                ],
            ),
        ]

        # Build deck
        deck_builder = DeckBuilder.from_hierarchy(["MedAnki", "Integration_Test"])

        for card in cards:
            if hasattr(card, "text"):
                deck_builder.add_cloze_card(card)
            else:
                deck_builder.add_vignette_card(card)

        deck = deck_builder.build()

        # Export
        exporter = APKGExporter()
        output_path = temp_output_dir / "full_pipeline.apkg"
        exporter.export(deck, str(output_path))

        # Verify
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        assert zipfile.is_zipfile(output_path)

        # Check contents
        with zipfile.ZipFile(output_path, 'r') as zf:
            assert "collection.anki2" in zf.namelist()

    def test_export_preserves_card_content(self, temp_output_dir: Path) -> None:
        """Test that card content is preserved through export."""
        deck_builder = DeckBuilder(name="MedAnki::Preservation_Test")

        original_text = "The {{c1::mitochondria}} is the powerhouse of the cell."

        deck_builder.add_cloze_card(
            MockClozeCard(text=original_text)
        )

        deck = deck_builder.build()

        # The note should contain our text
        assert len(deck.notes) == 1
        # genanki stores fields, first field should be the text
        assert original_text in deck.notes[0].fields[0]

    def test_export_handles_unicode(self, temp_output_dir: Path) -> None:
        """Test that export handles unicode characters correctly."""
        deck_builder = DeckBuilder(name="MedAnki::Unicode_Test")

        # Include various unicode characters
        unicode_text = "The patient's temperature was 38.5 degrees C."

        deck_builder.add_cloze_card(
            MockClozeCard(text=f"{{{{c1::{unicode_text}}}}}")
        )

        deck = deck_builder.build()
        exporter = APKGExporter()
        output_path = temp_output_dir / "unicode_test.apkg"

        # Should not raise
        exporter.export(deck, str(output_path))

        assert output_path.exists()
