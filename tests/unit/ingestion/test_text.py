from pathlib import Path

from medanki.ingestion.base import Document
from medanki.ingestion.text import MarkdownLoader, TextLoader

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "test_fixtures"


class TestTextLoader:
    def test_load_plain_text(self, tmp_path):
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text("This is plain text content.\nWith multiple lines.")

        loader = TextLoader()
        doc = loader.load(txt_file)

        assert isinstance(doc, Document)
        assert "This is plain text content" in doc.content
        assert "With multiple lines" in doc.content

    def test_handles_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        loader = TextLoader()
        doc = loader.load(empty_file)

        assert isinstance(doc, Document)
        assert doc.content == ""
        assert len(doc.sections) == 0


class TestMarkdownLoader:
    def test_load_markdown(self):
        loader = MarkdownLoader()
        doc = loader.load(FIXTURES_DIR / "sample.md")

        assert isinstance(doc, Document)
        assert "Introduction to Biology" in doc.content
        assert "Cell Structure" in doc.content

    def test_markdown_extracts_headers(self):
        loader = MarkdownLoader()
        doc = loader.load(FIXTURES_DIR / "sample.md")

        section_titles = [s.title for s in doc.sections]

        assert "Introduction to Biology" in section_titles
        assert "Cell Structure" in section_titles
        assert "Genetics" in section_titles
        assert "Prokaryotic Cells" in section_titles
        assert "Eukaryotic Cells" in section_titles
        assert "Summary" in section_titles

    def test_markdown_section_levels(self):
        loader = MarkdownLoader()
        doc = loader.load(FIXTURES_DIR / "sample.md")

        sections_by_title = {s.title: s for s in doc.sections}

        assert sections_by_title["Introduction to Biology"].level == 1
        assert sections_by_title["Cell Structure"].level == 2
        assert sections_by_title["Prokaryotic Cells"].level == 3

    def test_handles_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        loader = MarkdownLoader()
        doc = loader.load(empty_file)

        assert isinstance(doc, Document)
        assert doc.content == ""
        assert len(doc.sections) == 0
