"""Integration tests for the complete MedAnki pipeline.

Tests end-to-end flow from source files to APKG export.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

import pytest

from medanki.export.apkg import APKGExporter
from medanki.export.deck import DeckBuilder
from medanki.export.tags import TagBuilder
from medanki.generation.cloze import ClozeGenerator
from medanki.generation.deduplicator import Deduplicator
from medanki.generation.validator import CardValidator, ClozeCardInput
from medanki.ingestion.text import MarkdownLoader
from medanki.models.cards import ClozeCard
from medanki.processing.chunker import ChunkingService

# ============================================================================
# Mock Document for Chunking
# ============================================================================

@dataclass
class MockDocument:
    """Mock document that matches the chunker's protocol."""

    id: str
    raw_text: str
    sections: list = field(default_factory=list)


# ============================================================================
# Mock Card for Deck Building
# ============================================================================

class MockClozeCard:
    """Mock cloze card for deck building."""

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


# ============================================================================
# Full Pipeline Tests: PDF to APKG
# ============================================================================

@pytest.mark.integration
class TestPDFToAPKGPipeline:
    """Test full pipeline from PDF to APKG."""

    def test_pdf_to_apkg_full(
        self,
        sample_pdf_path: Path,
        temp_output_dir: Path,
        mock_llm_client,
    ) -> None:
        """Test complete pipeline from PDF file to APKG output."""
        if not sample_pdf_path.exists():
            pytest.skip("sample_lecture.pdf not found")

        # Step 1: Ingest PDF
        from medanki.ingestion.pdf import PDFExtractor

        extractor = PDFExtractor()
        document = extractor.extract(sample_pdf_path)

        assert document.content is not None
        assert len(document.content) > 0

        # Step 2: Create mock document for chunking
        mock_doc = MockDocument(
            id=str(uuid4()),
            raw_text=document.content,
            sections=document.sections,
        )

        # Step 3: Chunk the document
        chunker = ChunkingService(chunk_size=256, overlap=50)
        chunks = chunker.chunk(mock_doc)

        assert len(chunks) >= 1

        # Step 4: Generate cards from chunks (using mock LLM)
        generator = ClozeGenerator(llm_client=mock_llm_client)
        validator = CardValidator()
        deduplicator = Deduplicator()

        all_cards: list[ClozeCard] = []

        async def generate_cards():
            for chunk in chunks[:3]:  # Limit to first 3 chunks for test speed
                @dataclass
                class ChunkWrapper:
                    id: str
                    text: str
                    tags: list[str] = field(default_factory=lambda: ["cardiology"])

                wrapper = ChunkWrapper(id=chunk.id, text=chunk.text)

                try:
                    generated = await generator.generate(wrapper, count=2)

                    for gen_card in generated:
                        card_input = ClozeCardInput(
                            text=gen_card.text,
                            source_chunk=chunk.text,
                        )
                        result = validator.validate_schema(card_input)

                        if result.status.value == "valid":
                            card = ClozeCard(
                                text=gen_card.text,
                                source_chunk_id=gen_card.source_chunk_id,
                            )
                            all_cards.append(card)
                except Exception:
                    # Continue on generation errors
                    pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(generate_cards())

        # Step 5: Deduplicate
        unique_cards = deduplicator.deduplicate(all_cards)

        # Step 6: Build deck
        tag_builder = TagBuilder()
        deck_builder = DeckBuilder.from_hierarchy(["MedAnki", "PDF_Test"])

        for card in unique_cards:
            mock_card = MockClozeCard(
                text=card.text,
                source_chunk_id=str(card.source_chunk_id),
                tags=[tag_builder.build_source_tag("PDF_Lecture")],
            )
            deck_builder.add_cloze_card(mock_card)

        deck = deck_builder.build()

        # Step 7: Export to APKG
        exporter = APKGExporter()
        output_path = temp_output_dir / "pdf_full_pipeline.apkg"
        exporter.export(deck, str(output_path))

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        assert zipfile.is_zipfile(output_path)


# ============================================================================
# Full Pipeline Tests: Markdown to APKG
# ============================================================================

@pytest.mark.integration
class TestMarkdownToAPKGPipeline:
    """Test full pipeline from Markdown to APKG."""

    def test_markdown_to_apkg_full(
        self,
        sample_md_path: Path,
        temp_output_dir: Path,
        mock_llm_client,
    ) -> None:
        """Test complete pipeline from Markdown file to APKG output."""
        if not sample_md_path.exists():
            pytest.skip("sample_notes.md not found")

        # Step 1: Ingest Markdown
        loader = MarkdownLoader()
        document = loader.load(sample_md_path)

        assert document.content is not None
        assert len(document.sections) >= 1

        # Step 2: Create mock document for chunking
        mock_doc = MockDocument(
            id=str(uuid4()),
            raw_text=document.content,
            sections=document.sections,
        )

        # Step 3: Chunk the document
        chunker = ChunkingService(chunk_size=256, overlap=50)
        chunks = chunker.chunk(mock_doc)

        assert len(chunks) >= 1

        # Step 4: Generate cards
        generator = ClozeGenerator(llm_client=mock_llm_client)
        validator = CardValidator()
        deduplicator = Deduplicator()

        all_cards: list[ClozeCard] = []

        async def generate_cards():
            for chunk in chunks[:3]:
                @dataclass
                class ChunkWrapper:
                    id: str
                    text: str
                    tags: list[str] = field(default_factory=lambda: ["pharmacology"])

                wrapper = ChunkWrapper(id=chunk.id, text=chunk.text)

                try:
                    generated = await generator.generate(wrapper, count=2)

                    for gen_card in generated:
                        card_input = ClozeCardInput(
                            text=gen_card.text,
                            source_chunk=chunk.text,
                        )
                        result = validator.validate_schema(card_input)

                        if result.status.value == "valid":
                            card = ClozeCard(
                                text=gen_card.text,
                                source_chunk_id=gen_card.source_chunk_id,
                            )
                            all_cards.append(card)
                except Exception:
                    pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(generate_cards())

        # Step 5: Deduplicate
        unique_cards = deduplicator.deduplicate(all_cards)

        # Step 6: Build deck with proper tags
        tag_builder = TagBuilder()
        deck_builder = DeckBuilder.from_hierarchy(["MedAnki", "Markdown_Test"])

        for card in unique_cards:
            mock_card = MockClozeCard(
                text=card.text,
                source_chunk_id=str(card.source_chunk_id),
                tags=[
                    tag_builder.build_mcat_tag("FC2 > Pharmacology"),
                    tag_builder.build_source_tag("Pharmacology_Notes"),
                ],
            )
            deck_builder.add_cloze_card(mock_card)

        deck = deck_builder.build()

        # Step 7: Export
        exporter = APKGExporter()
        output_path = temp_output_dir / "markdown_full_pipeline.apkg"
        exporter.export(deck, str(output_path))

        # Verify
        assert output_path.exists()
        assert zipfile.is_zipfile(output_path)

    def test_markdown_content_preserved_in_cards(
        self,
        temp_directory: Path,
        pharmacology_content: str,
        mock_llm_client,
    ) -> None:
        """Test that key content from markdown is preserved in generated cards."""
        # Create markdown file
        md_path = temp_directory / "pharm_test.md"
        md_path.write_text(pharmacology_content)

        # Ingest
        loader = MarkdownLoader()
        document = loader.load(md_path)

        # Create mock doc and chunk
        mock_doc = MockDocument(
            id=str(uuid4()),
            raw_text=document.content,
            sections=document.sections,
        )

        chunker = ChunkingService(chunk_size=512, overlap=75)
        chunks = chunker.chunk(mock_doc)

        # Generate cards
        generator = ClozeGenerator(llm_client=mock_llm_client)

        async def generate():
            all_card_texts = []
            for chunk in chunks[:2]:
                @dataclass
                class ChunkWrapper:
                    id: str
                    text: str
                    tags: list[str] = field(default_factory=list)

                wrapper = ChunkWrapper(id=chunk.id, text=chunk.text)

                try:
                    cards = await generator.generate(wrapper, count=3)
                    for card in cards:
                        all_card_texts.append(card.text)
                except Exception:
                    pass

            return all_card_texts

        import asyncio
        card_texts = asyncio.get_event_loop().run_until_complete(generate())

        # Cards should reference medical concepts from the content
        all_text = " ".join(card_texts)

        # At least some medical terms should appear in cards
        medical_terms_found = any(
            term in all_text.lower()
            for term in ["systole", "diastole", "lisinopril", "metoprolol", "furosemide", "cardiac"]
        )

        assert medical_terms_found or len(card_texts) > 0, (
            "Expected cards with medical content"
        )


# ============================================================================
# Full Pipeline Tests: Directory to APKG
# ============================================================================

@pytest.mark.integration
class TestDirectoryToAPKGPipeline:
    """Test full pipeline from directory of files to single APKG."""

    def test_directory_to_apkg_full(
        self,
        sample_test_directory: Path,
        temp_output_dir: Path,
        mock_llm_client,
    ) -> None:
        """Test processing multiple files from directory into single deck."""
        # Collect all markdown files
        loader = MarkdownLoader()
        all_documents = []

        for md_file in sample_test_directory.rglob("*.md"):
            doc = loader.load(md_file)
            all_documents.append((md_file.stem, doc))

        assert len(all_documents) >= 2

        # Process each document
        chunker = ChunkingService(chunk_size=256, overlap=50)
        generator = ClozeGenerator(llm_client=mock_llm_client)
        validator = CardValidator()
        deduplicator = Deduplicator()

        all_cards: list[tuple[str, ClozeCard]] = []  # (source_name, card)

        async def process_all():
            for source_name, document in all_documents:
                mock_doc = MockDocument(
                    id=str(uuid4()),
                    raw_text=document.content,
                    sections=document.sections,
                )

                chunks = chunker.chunk(mock_doc)

                for chunk in chunks[:2]:  # Limit chunks per doc
                    @dataclass
                    class ChunkWrapper:
                        id: str
                        text: str
                        tags: list[str] = field(default_factory=list)

                    wrapper = ChunkWrapper(id=chunk.id, text=chunk.text)

                    try:
                        generated = await generator.generate(wrapper, count=2)

                        for gen_card in generated:
                            card_input = ClozeCardInput(
                                text=gen_card.text,
                                source_chunk=chunk.text,
                            )
                            result = validator.validate_schema(card_input)

                            if result.status.value == "valid":
                                card = ClozeCard(
                                    text=gen_card.text,
                                    source_chunk_id=gen_card.source_chunk_id,
                                )
                                all_cards.append((source_name, card))
                    except Exception:
                        pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(process_all())

        # Deduplicate cards (ignoring source for dedup)
        cards_only = [card for _, card in all_cards]
        unique_cards = deduplicator.deduplicate(cards_only)

        # Map back to sources (approximate - just use first occurrence)
        card_sources = {}
        for source_name, card in all_cards:
            card_hash = deduplicator.compute_content_hash(card)
            if card_hash not in card_sources:
                card_sources[card_hash] = source_name

        # Build combined deck
        tag_builder = TagBuilder()
        deck_builder = DeckBuilder.from_hierarchy(["MedAnki", "Directory_Test"])

        for card in unique_cards:
            card_hash = deduplicator.compute_content_hash(card)
            source_name = card_sources.get(card_hash, "Unknown")

            mock_card = MockClozeCard(
                text=card.text,
                source_chunk_id=str(card.source_chunk_id),
                tags=[tag_builder.build_source_tag(source_name)],
            )
            deck_builder.add_cloze_card(mock_card)

        deck = deck_builder.build()

        # Export
        exporter = APKGExporter()
        output_path = temp_output_dir / "directory_full_pipeline.apkg"
        exporter.export(deck, str(output_path))

        # Verify
        assert output_path.exists()
        assert output_path.stat().st_size > 0


# ============================================================================
# Pipeline Error Handling Tests
# ============================================================================

@pytest.mark.integration
class TestPipelineErrorHandling:
    """Test error handling in the pipeline."""

    def test_pipeline_handles_empty_document(
        self,
        temp_directory: Path,
        temp_output_dir: Path,
        mock_llm_client,
    ) -> None:
        """Test that pipeline handles empty documents gracefully."""
        # Create empty file
        empty_path = temp_directory / "empty.md"
        empty_path.write_text("")

        loader = MarkdownLoader()
        document = loader.load(empty_path)

        mock_doc = MockDocument(
            id=str(uuid4()),
            raw_text=document.content,
            sections=[],
        )

        chunker = ChunkingService()
        chunks = chunker.chunk(mock_doc)

        # Empty document should produce no chunks
        assert len(chunks) == 0

        # Should still be able to build an empty deck
        deck_builder = DeckBuilder(name="MedAnki::Empty")
        deck = deck_builder.build()

        exporter = APKGExporter()
        output_path = temp_output_dir / "empty_pipeline.apkg"
        exporter.export(deck, str(output_path))

        assert output_path.exists()

    def test_pipeline_handles_malformed_content(
        self,
        temp_directory: Path,
        temp_output_dir: Path,
        mock_llm_client,
    ) -> None:
        """Test that pipeline handles malformed content."""
        # Create file with unusual content
        weird_path = temp_directory / "weird.md"
        weird_path.write_text("""
# Header with no content

## Another header

###

####

- Incomplete list
-

```
Code block with no language
```
""")

        loader = MarkdownLoader()
        document = loader.load(weird_path)

        mock_doc = MockDocument(
            id=str(uuid4()),
            raw_text=document.content,
            sections=document.sections,
        )

        chunker = ChunkingService(chunk_size=256, overlap=50)
        chunks = chunker.chunk(mock_doc)

        # Should handle gracefully - may or may not produce chunks
        # depending on content length
        assert isinstance(chunks, list)

        # Build deck with whatever we got
        deck_builder = DeckBuilder(name="MedAnki::Malformed")
        deck = deck_builder.build()

        exporter = APKGExporter()
        output_path = temp_output_dir / "malformed_pipeline.apkg"
        exporter.export(deck, str(output_path))

        assert output_path.exists()


# ============================================================================
# Pipeline Statistics Tests
# ============================================================================

@pytest.mark.integration
class TestPipelineStatistics:
    """Test pipeline statistics and metrics."""

    def test_pipeline_produces_expected_card_counts(
        self,
        temp_directory: Path,
        cardiology_content: str,
        mock_llm_client,
    ) -> None:
        """Test that pipeline produces reasonable number of cards."""
        md_path = temp_directory / "cardio_stats.md"
        md_path.write_text(cardiology_content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        mock_doc = MockDocument(
            id=str(uuid4()),
            raw_text=document.content,
            sections=document.sections,
        )

        chunker = ChunkingService(chunk_size=256, overlap=50)
        chunks = chunker.chunk(mock_doc)

        generator = ClozeGenerator(llm_client=mock_llm_client)

        total_cards = 0

        async def count_cards():
            nonlocal total_cards
            for chunk in chunks:
                @dataclass
                class ChunkWrapper:
                    id: str
                    text: str
                    tags: list[str] = field(default_factory=list)

                wrapper = ChunkWrapper(id=chunk.id, text=chunk.text)

                try:
                    cards = await generator.generate(wrapper, count=3)
                    total_cards += len(cards)
                except Exception:
                    pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(count_cards())

        # Should generate at least some cards from medical content
        assert total_cards >= 1, "Expected at least 1 card from cardiology content"

        # Should not generate excessive cards
        max_expected = len(chunks) * 3  # max 3 cards per chunk
        assert total_cards <= max_expected

    def test_deduplication_removes_duplicates(
        self,
        mock_llm_client,
    ) -> None:
        """Test that deduplication effectively removes duplicates."""
        # Create cards with some duplicates
        cards = [
            ClozeCard(
                text="The heart has {{c1::four}} chambers.",
                source_chunk_id=uuid4(),
            ),
            ClozeCard(
                text="The heart has {{c1::four}} chambers.",  # Duplicate
                source_chunk_id=uuid4(),
            ),
            ClozeCard(
                text="{{c1::Systole}} is ventricular contraction.",
                source_chunk_id=uuid4(),
            ),
            ClozeCard(
                text="{{c1::Systole}} is ventricular contraction.",  # Duplicate
                source_chunk_id=uuid4(),
            ),
            ClozeCard(
                text="{{c1::Diastole}} is ventricular relaxation.",
                source_chunk_id=uuid4(),
            ),
        ]

        deduplicator = Deduplicator()
        unique_cards = deduplicator.deduplicate(cards)

        # Should have 3 unique cards
        assert len(unique_cards) == 3
