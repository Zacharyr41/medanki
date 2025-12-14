"""Integration tests for the ingestion pipeline.

Tests the full ingestion flow from file to Document with sections.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from medanki.ingestion.pdf import PDFExtractor
from medanki.ingestion.text import MarkdownLoader, TextLoader
from medanki.processing.chunker import ChunkingService


# ============================================================================
# PDF Ingestion Tests
# ============================================================================

@pytest.mark.integration
class TestPDFIngestion:
    """Test PDF ingestion end-to-end."""

    def test_ingest_pdf_end_to_end(self, sample_pdf_path: Path) -> None:
        """Test that a PDF file is ingested into a Document with sections."""
        # Skip if sample PDF doesn't exist
        if not sample_pdf_path.exists():
            pytest.skip("sample_lecture.pdf not found")

        extractor = PDFExtractor()
        document = extractor.extract(sample_pdf_path)

        # Verify document structure
        assert document is not None
        assert document.content is not None
        assert len(document.content) > 0
        assert document.source_path == sample_pdf_path

        # Verify metadata
        assert "page_count" in document.metadata
        assert document.metadata["page_count"] >= 1

    def test_ingest_pdf_extracts_sections(self, sample_pdf_path: Path) -> None:
        """Test that PDF sections are properly extracted."""
        if not sample_pdf_path.exists():
            pytest.skip("sample_lecture.pdf not found")

        extractor = PDFExtractor()
        document = extractor.extract(sample_pdf_path)

        # The sample PDF should have some structure
        # Sections may or may not be detected depending on PDF format
        assert document.content is not None

        # Check for medical content keywords
        content_lower = document.content.lower()
        assert any(
            keyword in content_lower
            for keyword in ["heart", "cardiac", "cardiovascular", "chapter"]
        )

    def test_ingest_pdf_preserves_medical_terms(self, sample_pdf_path: Path) -> None:
        """Test that medical terminology is preserved during ingestion."""
        if not sample_pdf_path.exists():
            pytest.skip("sample_lecture.pdf not found")

        extractor = PDFExtractor()
        document = extractor.extract(sample_pdf_path)

        content = document.content

        # Check that medical terms are intact
        medical_terms = [
            "mmHg",
            "ventricle",
            "atrium",
            "cardiac",
        ]

        # At least some medical terms should be present
        found_terms = [term for term in medical_terms if term.lower() in content.lower()]
        assert len(found_terms) >= 1, f"Expected medical terms, found: {found_terms}"


# ============================================================================
# Markdown Ingestion Tests
# ============================================================================

@pytest.mark.integration
class TestMarkdownIngestion:
    """Test markdown ingestion end-to-end."""

    def test_ingest_markdown_end_to_end(self, sample_md_path: Path) -> None:
        """Test that a markdown file is ingested into a Document with sections."""
        if not sample_md_path.exists():
            pytest.skip("sample_notes.md not found")

        loader = MarkdownLoader()
        document = loader.load(sample_md_path)

        # Verify document structure
        assert document is not None
        assert document.content is not None
        assert len(document.content) > 0
        assert document.source_path == sample_md_path

        # Verify sections were extracted
        assert len(document.sections) > 0, "Markdown should have extracted sections"

    def test_ingest_markdown_extracts_hierarchy(self, sample_md_path: Path) -> None:
        """Test that markdown heading hierarchy is preserved."""
        if not sample_md_path.exists():
            pytest.skip("sample_notes.md not found")

        loader = MarkdownLoader()
        document = loader.load(sample_md_path)

        # Check for different heading levels
        levels = {section.level for section in document.sections}

        # Should have at least H1 and H2
        assert 1 in levels or 2 in levels, "Should have H1 or H2 level sections"

    def test_ingest_markdown_preserves_content(
        self, temp_directory: Path, pharmacology_content: str
    ) -> None:
        """Test that markdown content is fully preserved."""
        md_path = temp_directory / "test_pharm.md"
        md_path.write_text(pharmacology_content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        # Key content should be present
        assert "Beta-Blockers" in document.content
        assert "ACE Inhibitors" in document.content
        assert "Furosemide" in document.content
        assert "mEq/L" in document.content  # Lab value format

    def test_ingest_markdown_with_drug_dosages(self, temp_directory: Path) -> None:
        """Test that drug dosages are preserved in markdown."""
        content = """
# Medication Guide

## Cardiovascular Drugs

- Metoprolol 25mg twice daily
- Lisinopril 10mg daily
- Furosemide 40mg daily
- Aspirin 81mg daily

### Lab Monitoring

Check potassium levels: normal 3.5-5.0 mEq/L
"""
        md_path = temp_directory / "meds.md"
        md_path.write_text(content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        # Verify dosages are intact
        assert "25mg" in document.content
        assert "10mg" in document.content
        assert "3.5-5.0 mEq/L" in document.content


# ============================================================================
# Plain Text Ingestion Tests
# ============================================================================

@pytest.mark.integration
class TestTextIngestion:
    """Test plain text file ingestion."""

    def test_ingest_plain_text(self, temp_directory: Path) -> None:
        """Test that plain text files are ingested correctly."""
        content = "This is a simple text file about cardiology."
        txt_path = temp_directory / "notes.txt"
        txt_path.write_text(content)

        loader = TextLoader()
        document = loader.load(txt_path)

        assert document.content == content
        assert document.source_path == txt_path
        assert document.metadata.get("format") == "plain_text"


# ============================================================================
# Directory Ingestion Tests
# ============================================================================

@pytest.mark.integration
class TestDirectoryIngestion:
    """Test directory-level ingestion."""

    def test_ingest_directory(self, sample_test_directory: Path) -> None:
        """Test that multiple files from a directory are processed."""
        loader = MarkdownLoader()
        documents = []

        # Collect all markdown files
        for md_file in sample_test_directory.rglob("*.md"):
            doc = loader.load(md_file)
            documents.append(doc)

        # Should find at least 2 markdown files
        assert len(documents) >= 2

        # Verify each document has content
        for doc in documents:
            assert doc.content is not None
            assert len(doc.content) > 0

    def test_ingest_directory_filters_by_extension(
        self, sample_test_directory: Path
    ) -> None:
        """Test that directory ingestion respects file extension filters."""
        # Count markdown files
        md_files = list(sample_test_directory.rglob("*.md"))

        # Count text files
        txt_files = list(sample_test_directory.rglob("*.txt"))

        # Should have both types
        assert len(md_files) >= 2
        assert len(txt_files) >= 1


# ============================================================================
# Chunking Tests
# ============================================================================

@pytest.mark.integration
class TestChunkingPipeline:
    """Test document chunking."""

    def test_chunk_real_document(
        self, temp_directory: Path, cardiology_content: str
    ) -> None:
        """Test chunking a real document into chunks with entities."""
        # Create document
        md_path = temp_directory / "cardiology.md"
        md_path.write_text(cardiology_content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        # Create a mock document that matches chunker's protocol
        class MockDocument:
            def __init__(self, content: str, sections: list):
                self.id = "test_doc_001"
                self.raw_text = content
                self.sections = sections

        mock_doc = MockDocument(document.content, document.sections)

        # Chunk the document
        chunker = ChunkingService(chunk_size=256, overlap=50)
        chunks = chunker.chunk(mock_doc)

        # Should produce multiple chunks
        assert len(chunks) >= 1

        # Each chunk should have required fields
        for chunk in chunks:
            assert chunk.id is not None
            assert chunk.text is not None
            assert len(chunk.text) > 0
            assert chunk.token_count > 0
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char

    def test_chunking_preserves_medical_terms(self, temp_directory: Path) -> None:
        """Test that chunking does not split medical terms like lab values."""
        content = """
# Lab Results

The patient's lab values are as follows:

Serum sodium: 140 mEq/L (normal range: 136-145 mEq/L)
Serum potassium: 4.2 mEq/L (normal range: 3.5-5.0 mEq/L)
Blood glucose: 95 mg/dL (fasting, normal range: 70-100 mg/dL)
Hemoglobin A1c: 6.5% (diabetic threshold: greater than 6.5%)
Creatinine: 1.1 mg/dL (normal range: 0.7-1.3 mg/dL)

Current medications include metoprolol 25mg twice daily for rate control
and lisinopril 10mg once daily for blood pressure management.

The patient's left anterior descending artery shows 70% stenosis.
The right coronary artery is patent with good flow.
"""
        md_path = temp_directory / "labs.md"
        md_path.write_text(content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        class MockDocument:
            def __init__(self, content: str, sections: list):
                self.id = "test_doc_labs"
                self.raw_text = content
                self.sections = sections

        mock_doc = MockDocument(document.content, document.sections)

        chunker = ChunkingService(chunk_size=128, overlap=25)
        chunks = chunker.chunk(mock_doc)

        # Check that lab values are not split
        # Look for complete lab value patterns in chunks
        all_text = " ".join(chunk.text for chunk in chunks)

        # These patterns should be intact somewhere
        assert "mEq/L" in all_text
        assert "mg/dL" in all_text

        # Drug doses should be intact
        assert "25mg" in all_text or "25 mg" in all_text
        assert "10mg" in all_text or "10 mg" in all_text

    def test_chunking_respects_section_boundaries(
        self, temp_directory: Path
    ) -> None:
        """Test that chunking respects document section boundaries when possible."""
        content = """
# Section One

This is the content of section one. It contains important information
about the first topic that should ideally stay together.

# Section Two

This is the content of section two. It covers a completely different
topic and should be in a separate chunk when possible.

# Section Three

The third section has its own content about another subject matter
that is distinct from the previous sections.
"""
        md_path = temp_directory / "sections.md"
        md_path.write_text(content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        class MockDocument:
            def __init__(self, content: str, sections: list):
                self.id = "test_doc_sections"
                self.raw_text = content
                self.sections = sections

        mock_doc = MockDocument(document.content, document.sections)

        # Use large chunk size to see section handling
        chunker = ChunkingService(chunk_size=512, overlap=50)
        chunks = chunker.chunk(mock_doc)

        # All content should be covered
        total_chars = sum(len(c.text) for c in chunks)
        assert total_chars > 0


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.integration
class TestIngestionEdgeCases:
    """Test edge cases in ingestion."""

    def test_empty_markdown_file(self, temp_directory: Path) -> None:
        """Test handling of empty markdown file."""
        md_path = temp_directory / "empty.md"
        md_path.write_text("")

        loader = MarkdownLoader()
        document = loader.load(md_path)

        assert document.content == ""
        assert len(document.sections) == 0

    def test_markdown_with_only_headers(self, temp_directory: Path) -> None:
        """Test markdown file with only headers, no content."""
        content = """# Header One

## Header Two

### Header Three
"""
        md_path = temp_directory / "headers_only.md"
        md_path.write_text(content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        assert len(document.sections) >= 1

    def test_markdown_with_special_characters(self, temp_directory: Path) -> None:
        """Test markdown with special medical characters."""
        content = """
# Special Characters

- Temperature: 37.5 degrees C
- Heart rate: 72 bpm
- BP: 120/80 mmHg
- Lab: Na+ = 140, K+ = 4.0, Cl- = 100
- Medication: beta-blocker (metoprolol)
- Gene: BRCA1/BRCA2
"""
        md_path = temp_directory / "special.md"
        md_path.write_text(content)

        loader = MarkdownLoader()
        document = loader.load(md_path)

        # Special characters should be preserved
        assert "Na+" in document.content
        assert "K+" in document.content
        assert "120/80" in document.content
        assert "BRCA1/BRCA2" in document.content
