"""Tests for APKG export functionality."""

import os
import tempfile
import zipfile

from packages.core.src.medanki.export.apkg import APKGExporter
from packages.core.src.medanki.export.deck import DeckBuilder
from tests.conftest import ClozeCard, VignetteCard


class TestAPKGExporter:
    def test_exports_apkg_file(self, tmp_path):
        """Creates .apkg file."""
        builder = DeckBuilder("Test Export")
        card = ClozeCard(
            id="test_001",
            text="The {{c1::mitochondria}} is the powerhouse of the cell",
            source_chunk_id="chunk_001",
        )
        builder.add_cloze_card(card)
        deck = builder.build()

        exporter = APKGExporter()
        output_path = tmp_path / "test.apkg"
        exporter.export(deck, str(output_path))

        assert output_path.exists()
        assert output_path.suffix == ".apkg"

    def test_apkg_importable(self, tmp_path):
        """File structure valid - apkg is a zip file."""
        builder = DeckBuilder("Test Import")
        card = ClozeCard(
            id="test_001",
            text="{{c1::DNA}} encodes genetic information",
            source_chunk_id="chunk_001",
        )
        builder.add_cloze_card(card)
        deck = builder.build()

        exporter = APKGExporter()
        output_path = tmp_path / "test_import.apkg"
        exporter.export(deck, str(output_path))

        assert zipfile.is_zipfile(str(output_path))
        with zipfile.ZipFile(str(output_path), "r") as zf:
            names = zf.namelist()
            assert "collection.anki2" in names or any("anki2" in n for n in names)

    def test_includes_media(self, tmp_path):
        """Images packaged correctly."""
        builder = DeckBuilder("Test Media")
        card = ClozeCard(
            id="test_001",
            text="{{c1::Heart}} diagram <img src='heart.png'>",
            source_chunk_id="chunk_001",
        )
        builder.add_cloze_card(card)
        deck = builder.build()

        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "heart.png").write_bytes(b"fake png data")

        exporter = APKGExporter()
        output_path = tmp_path / "test_media.apkg"
        exporter.export(deck, str(output_path), media_files=[str(media_dir / "heart.png")])

        with zipfile.ZipFile(str(output_path), "r") as zf:
            names = zf.namelist()
            assert "media" in names or any("heart" in n.lower() for n in names) or "0" in names

    def test_multiple_decks(self, tmp_path):
        """Can export multiple decks."""
        builders = []
        for i in range(3):
            b = DeckBuilder(f"Deck {i}")
            card = ClozeCard(
                id=f"test_{i:03d}",
                text=f"The {{{{c1::concept{i}}}}} is important",
                source_chunk_id=f"chunk_{i:03d}",
            )
            b.add_cloze_card(card)
            builders.append(b)

        decks = [b.build() for b in builders]

        exporter = APKGExporter()
        output_path = tmp_path / "multi_deck.apkg"
        exporter.export_multiple(decks, str(output_path))

        assert output_path.exists()

    def test_cleanup_temp_files(self, tmp_path):
        """Temp files cleaned up after export."""
        builder = DeckBuilder("Cleanup Test")
        card = ClozeCard(id="test_001", text="{{c1::Test}} cleanup", source_chunk_id="chunk_001")
        builder.add_cloze_card(card)
        deck = builder.build()

        exporter = APKGExporter()
        output_path = tmp_path / "cleanup.apkg"
        exporter.export(deck, str(output_path))

        temp_dir = tempfile.gettempdir()
        medanki_temps = [f for f in os.listdir(temp_dir) if "medanki" in f.lower()]
        assert len(medanki_temps) == 0

    def test_export_with_vignette_cards(self, tmp_path):
        builder = DeckBuilder("Vignette Export")
        card = VignetteCard(
            id="vig_001",
            front="A 25-year-old patient presents with...",
            answer="Appendicitis",
            explanation="Classic presentation",
            distinguishing_feature="RLQ pain",
            source_chunk_id="chunk_001",
        )
        builder.add_vignette_card(card)
        deck = builder.build()

        exporter = APKGExporter()
        output_path = tmp_path / "vignette.apkg"
        exporter.export(deck, str(output_path))

        assert output_path.exists()

    def test_deck_contains_all_cards(self, tmp_path):
        """Deck contains all cards that were added."""
        builder = DeckBuilder("Card Count Test")
        for i in range(5):
            card = ClozeCard(
                id=f"test_{i:03d}",
                text=f"The {{{{c1::concept{i}}}}} is important",
                source_chunk_id=f"chunk_{i:03d}",
            )
            builder.add_cloze_card(card)
        deck = builder.build()

        assert len(deck.notes) == 5

    def test_deck_has_stable_ids(self, tmp_path):
        """Same deck name produces same deck ID."""
        builder1 = DeckBuilder("Stable ID Test")
        card1 = ClozeCard(
            id="test_001", text="The {{c1::heart}} pumps blood", source_chunk_id="chunk_001"
        )
        builder1.add_cloze_card(card1)
        deck1 = builder1.build()

        builder2 = DeckBuilder("Stable ID Test")
        card2 = ClozeCard(
            id="test_002", text="The {{c1::lungs}} exchange gases", source_chunk_id="chunk_002"
        )
        builder2.add_cloze_card(card2)
        deck2 = builder2.build()

        assert deck1.deck_id == deck2.deck_id

    def test_deck_name_matches_exam_type(self, tmp_path):
        """Deck name reflects exam type."""
        builder = DeckBuilder("MedAnki::USMLE_Step1::Cardiology")
        card = ClozeCard(
            id="test_001", text="The {{c1::heart}} pumps blood", source_chunk_id="chunk_001"
        )
        builder.add_cloze_card(card)
        deck = builder.build()

        assert "USMLE" in deck.name or "MedAnki" in deck.name

    def test_build_tags_from_topics(self, tmp_path):
        """Tags are built from topic matches."""
        from packages.core.src.medanki.export.tags import TagBuilder

        tag_builder = TagBuilder()
        topics = [
            {"path": "Cardiology > Heart Failure"},
            {"path": "Pharmacology > Beta Blockers"},
        ]

        tags = [tag_builder.build_hierarchical_tag(t["path"].split(" > ")) for t in topics]

        assert len(tags) == 2
        assert all("::" in tag for tag in tags)

    def test_tags_use_hierarchical_format(self, tmp_path):
        """Tags use :: separator for hierarchy."""
        from packages.core.src.medanki.export.tags import TagBuilder

        tag_builder = TagBuilder()
        tag = tag_builder.build_hierarchical_tag(["USMLE", "Step1", "Cardiology", "CHF"])

        assert tag == "#USMLE::Step1::Cardiology::CHF"
        assert tag.count("::") == 3
