from pathlib import Path

import pytest

from medanki.ingestion.base import Document, IngestionError
from medanki.ingestion.pdf import PDFExtractor

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "test_fixtures"


class TestPDFExtractor:
    def test_extract_text_from_pdf(self):
        extractor = PDFExtractor()
        doc = extractor.extract(FIXTURES_DIR / "sample.pdf")

        assert "Introduction" in doc.content
        assert "Cell Biology" in doc.content
        assert "Biology is the study of living organisms" in doc.content

    def test_extract_preserves_sections(self):
        extractor = PDFExtractor()
        doc = extractor.extract(FIXTURES_DIR / "sample.pdf")

        section_titles = [s.title for s in doc.sections]
        assert any("Introduction" in title for title in section_titles)
        assert any("Cell Biology" in title for title in section_titles)

    def test_extract_includes_page_numbers(self):
        extractor = PDFExtractor()
        doc = extractor.extract(FIXTURES_DIR / "sample.pdf")

        assert doc.metadata.get("page_count") == 2
        assert len(doc.sections) >= 1
        for section in doc.sections:
            assert section.page_number is not None
            assert section.page_number >= 1

    def test_handles_scanned_pdf(self):
        extractor = PDFExtractor()
        scanned_path = FIXTURES_DIR / "scanned.pdf"

        if not scanned_path.exists():
            pytest.skip("No scanned PDF fixture available")

        doc = extractor.extract(scanned_path)
        assert doc is not None

    def test_handles_corrupted_pdf(self, tmp_path):
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"not a valid pdf content")

        extractor = PDFExtractor()
        with pytest.raises(IngestionError):
            extractor.extract(corrupted_pdf)

    def test_returns_document_model(self):
        extractor = PDFExtractor()
        doc = extractor.extract(FIXTURES_DIR / "sample.pdf")

        assert isinstance(doc, Document)
        assert doc.content is not None
        assert doc.sections is not None
        assert doc.metadata is not None
        assert doc.source_path == FIXTURES_DIR / "sample.pdf"
