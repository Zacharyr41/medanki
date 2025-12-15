"""End-to-end tests for the PDF to flashcard pipeline."""

from pathlib import Path

import pytest

CIMT_PDF_PATH = Path(
    "/Users/zacharyrothstein/Downloads/DOC/Carotid Intima-Media Thickness_ Rise, Fall, and Rehabilitation of a Cardiovascular Biomarker.pdf"
)


@pytest.fixture
def cimt_pdf():
    """Path to the cIMT PDF for testing."""
    if not CIMT_PDF_PATH.exists():
        pytest.skip(f"Test PDF not found: {CIMT_PDF_PATH}")
    return CIMT_PDF_PATH


class TestPDFIngestion:
    """Tests for PDF extraction."""

    @pytest.mark.e2e
    def test_extract_text_from_cimt_pdf(self, cimt_pdf):
        """Should extract text from the cIMT PDF."""
        from medanki.ingestion.pdf import PDFExtractor

        extractor = PDFExtractor()
        document = extractor.extract(cimt_pdf)

        assert document is not None
        assert len(document.content) > 0
        assert (
            "intima-media" in document.content.lower()
            or "atherosclerosis" in document.content.lower()
        )

    @pytest.mark.e2e
    def test_chunking_cimt_content(self, cimt_pdf):
        """Should chunk the cIMT content into processable segments."""
        from dataclasses import dataclass

        from medanki.ingestion.pdf import PDFExtractor
        from medanki.processing.chunker import ChunkingService

        @dataclass
        class ChunkableDoc:
            id: str
            raw_text: str
            sections: list

        extractor = PDFExtractor()
        document = extractor.extract(cimt_pdf)

        chunkable = ChunkableDoc(
            id="test-doc",
            raw_text=document.content,
            sections=document.sections,
        )

        chunker = ChunkingService()
        chunks = chunker.chunk(chunkable)

        assert len(chunks) > 0
        assert all(len(chunk.text) > 0 for chunk in chunks)


class TestClassificationIntegration:
    """Tests for classification of cIMT content."""

    @pytest.mark.e2e
    @pytest.mark.integration
    def test_cimt_chunks_classify_to_cardiovascular(self, cimt_pdf):
        """cIMT chunks should classify to cardiovascular topics."""
        from dataclasses import dataclass

        import weaviate

        from medanki.ingestion.pdf import PDFExtractor
        from medanki.processing.chunker import ChunkingService
        from medanki.services.taxonomy_indexer import TaxonomyIndexer

        @dataclass
        class ChunkableDoc:
            id: str
            raw_text: str
            sections: list

        taxonomy_dir = Path(__file__).parent.parent.parent / "data" / "taxonomies"

        extractor = PDFExtractor()
        document = extractor.extract(cimt_pdf)

        chunkable = ChunkableDoc(
            id="test-doc",
            raw_text=document.content,
            sections=document.sections,
        )

        chunker = ChunkingService()
        chunks = chunker.chunk(chunkable)

        client = weaviate.connect_to_local(port=8080)
        try:
            indexer = TaxonomyIndexer(client, taxonomy_dir)

            collection = client.collections.get("TaxonomyTopic")
            count_result = collection.aggregate.over_all(total_count=True)
            if count_result.total_count == 0:
                indexer.index_exam("USMLE_STEP1")

            cardio_chunks = 0
            for chunk in chunks[:5]:
                results = indexer.search(chunk.text, exam_type="USMLE_STEP1", limit=3)
                if results:
                    for r in results:
                        if (
                            "SYS3" in r["topic_id"]
                            or "Cardiovascular" in r["title"]
                            or "Vascular" in r["title"]
                        ):
                            cardio_chunks += 1
                            break

            assert cardio_chunks > 0, "Expected at least one chunk to classify as cardiovascular"
        finally:
            client.close()


class TestCardGeneration:
    """Tests for card generation quality."""

    @pytest.mark.e2e
    @pytest.mark.vcr()
    async def test_generated_cards_test_mechanisms(self, cimt_pdf):
        """Generated cards should test mechanisms, not trivia."""
        import os
        import re
        from dataclasses import dataclass
        from uuid import uuid4

        from medanki.generation.cloze import ClozeGenerator
        from medanki.ingestion.pdf import PDFExtractor
        from medanki.processing.chunker import ChunkingService
        from medanki.services.llm import ClaudeClient

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        @dataclass
        class ChunkableDoc:
            id: str
            raw_text: str
            sections: list

        extractor = PDFExtractor()
        document = extractor.extract(cimt_pdf)

        chunkable = ChunkableDoc(
            id="test-doc",
            raw_text=document.content,
            sections=document.sections,
        )

        chunker = ChunkingService()
        chunks = chunker.chunk(chunkable)

        client = ClaudeClient(api_key=api_key)
        generator = ClozeGenerator(llm_client=client)

        relevant_chunk = None
        for chunk in chunks:
            if "atherosclerosis" in chunk.text.lower() or "intima" in chunk.text.lower():
                relevant_chunk = chunk
                break

        if not relevant_chunk:
            relevant_chunk = chunks[0]

        cards = await generator.generate(
            content=relevant_chunk.text,
            source_chunk_id=uuid4(),
            topic_id="SYS3",
            topic_context="Topic: Cardiovascular System > Vascular Disorders",
            num_cards=3,
        )

        assert len(cards) > 0, "Should generate at least one card"

        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        trivia_patterns = [
            re.compile(r"\b[A-Z]{2,}(?:-[A-Z]+)*\s+(?:trial|study|cohort)\b", re.IGNORECASE),
            re.compile(r"\bHR\s*[=:]\s*\d+\.?\d*"),
            re.compile(r"\bp\s*[<>=]\s*0?\.\d+"),
            re.compile(r"\b(?:19|20)\d{2}\s+(?:guidelines?|recommendations?)\b", re.IGNORECASE),
        ]

        for card in cards:
            answers = [m.group(1) for m in cloze_pattern.finditer(card.text)]
            for answer in answers:
                for pattern in trivia_patterns:
                    assert not pattern.search(answer), (
                        f"Card contains trivia: {answer} in {card.text}"
                    )
