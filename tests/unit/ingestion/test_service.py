"""Tests for the ingestion service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

if TYPE_CHECKING:
    from medanki.ingestion.service import IngestionService


@dataclass
class MockDocument:
    """Mock document for testing."""

    raw_text: str = ""
    sections: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    content_type: Any = None


@pytest.fixture
def mock_pdf_extractor() -> AsyncMock:
    """Create a mock PDF extractor."""
    extractor = AsyncMock()
    extractor.extract.return_value = MockDocument(
        raw_text="PDF content here.",
        sections=[],
        metadata={"page_count": 5},
    )
    return extractor


@pytest.fixture
def mock_text_loader() -> AsyncMock:
    """Create a mock text loader."""
    loader = AsyncMock()
    loader.load.return_value = MockDocument(
        raw_text="Text content here.",
        sections=[],
        metadata={},
    )
    return loader


@pytest.fixture
def ingestion_service(
    mock_pdf_extractor: AsyncMock,
    mock_text_loader: AsyncMock,
) -> IngestionService:
    """Create an IngestionService instance with mocked dependencies."""
    from medanki.ingestion.service import IngestionService

    return IngestionService(
        pdf_extractor=mock_pdf_extractor,
        text_loader=mock_text_loader,
    )


@pytest.fixture
def temp_directory(tmp_path: Path) -> Path:
    """Create a temporary directory with test files."""
    (tmp_path / "document.pdf").write_bytes(b"%PDF-1.4 test")
    (tmp_path / "notes.md").write_text("# Notes\n\nSome content.")
    (tmp_path / "readme.txt").write_text("Plain text content.")
    (tmp_path / ".hidden_file.txt").write_text("Hidden content.")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.pdf").write_bytes(b"%PDF-1.4 nested")
    (subdir / "nested.md").write_text("# Nested\n\nNested content.")

    return tmp_path


class TestFactoryPattern:
    """Tests for extractor factory pattern."""

    @pytest.mark.asyncio
    async def test_ingest_pdf_uses_pdf_extractor(
        self,
        ingestion_service: IngestionService,
        mock_pdf_extractor: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """.pdf routes to PDFExtractor."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        await ingestion_service.ingest_file(pdf_file)

        mock_pdf_extractor.extract.assert_called_once()
        call_args = mock_pdf_extractor.extract.call_args
        assert call_args[0][0] == pdf_file

    @pytest.mark.asyncio
    async def test_ingest_markdown_uses_text_loader(
        self,
        ingestion_service: IngestionService,
        mock_text_loader: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """.md routes to MarkdownLoader."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Markdown\n\nContent here.")

        await ingestion_service.ingest_file(md_file)

        mock_text_loader.load.assert_called_once()
        call_args = mock_text_loader.load.call_args
        assert call_args[0][0] == md_file

    @pytest.mark.asyncio
    async def test_ingest_txt_uses_text_loader(
        self,
        ingestion_service: IngestionService,
        mock_text_loader: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """.txt routes to TextLoader."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text content.")

        await ingestion_service.ingest_file(txt_file)

        mock_text_loader.load.assert_called_once()
        call_args = mock_text_loader.load.call_args
        assert call_args[0][0] == txt_file

    @pytest.mark.asyncio
    async def test_unsupported_format_raises(
        self,
        ingestion_service: IngestionService,
        tmp_path: Path,
    ) -> None:
        """.docx raises IngestionError."""
        from medanki.ingestion.errors import IngestionError

        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(b"fake docx content")

        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.ingest_file(docx_file)

        assert "unsupported" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_detects_content_type(
        self,
        ingestion_service: IngestionService,
        mock_text_loader: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Sets correct ContentType enum."""
        from medanki.models.enums import ContentType

        mock_text_loader.load.return_value = MockDocument(
            raw_text="Markdown content.",
            sections=[],
            metadata={},
            content_type=ContentType.MARKDOWN,
        )

        md_file = tmp_path / "test.md"
        md_file.write_text("# Markdown\n\nContent.")

        document = await ingestion_service.ingest_file(md_file)

        assert document.content_type == ContentType.MARKDOWN


class TestDirectoryProcessing:
    """Tests for directory processing functionality."""

    @pytest.mark.asyncio
    async def test_ingest_directory_finds_files(
        self,
        ingestion_service: IngestionService,
        temp_directory: Path,
        mock_pdf_extractor: AsyncMock,
        mock_text_loader: AsyncMock,
    ) -> None:
        """Recursively finds supported files."""
        documents = await ingestion_service.ingest_directory(temp_directory)

        total_calls = (
            mock_pdf_extractor.extract.call_count + mock_text_loader.load.call_count
        )
        assert total_calls == 5
        assert len(documents) == 5

    @pytest.mark.asyncio
    async def test_ingest_directory_skips_hidden(
        self,
        ingestion_service: IngestionService,
        temp_directory: Path,
        mock_text_loader: AsyncMock,
    ) -> None:
        """Ignores .dotfiles."""
        await ingestion_service.ingest_directory(temp_directory)

        for call in mock_text_loader.load.call_args_list:
            file_path = call[0][0]
            assert not file_path.name.startswith(".")

    @pytest.mark.asyncio
    async def test_ingest_directory_returns_documents(
        self,
        ingestion_service: IngestionService,
        temp_directory: Path,
    ) -> None:
        """List of Document objects."""
        documents = await ingestion_service.ingest_directory(temp_directory)

        assert isinstance(documents, list)
        for doc in documents:
            assert hasattr(doc, "raw_text")
            assert hasattr(doc, "source_path")
            assert hasattr(doc, "content_type")

    @pytest.mark.asyncio
    async def test_empty_directory_returns_empty(
        self,
        ingestion_service: IngestionService,
        tmp_path: Path,
    ) -> None:
        """No files = empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        documents = await ingestion_service.ingest_directory(empty_dir)

        assert documents == []

    @pytest.mark.asyncio
    async def test_ingest_directory_non_recursive(
        self,
        ingestion_service: IngestionService,
        temp_directory: Path,
    ) -> None:
        """Non-recursive mode only processes top-level files."""
        documents = await ingestion_service.ingest_directory(
            temp_directory, recursive=False
        )

        assert len(documents) == 3


class TestNormalization:
    """Tests for text normalization functionality."""

    @pytest.mark.asyncio
    async def test_normalizes_whitespace(
        self,
        ingestion_service: IngestionService,
        mock_text_loader: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Collapses multiple spaces/newlines."""
        mock_text_loader.load.return_value = MockDocument(
            raw_text="Text   with    multiple     spaces\n\n\n\nand newlines.",
            sections=[],
            metadata={},
        )

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Content")

        document = await ingestion_service.ingest_file(txt_file)

        assert "   " not in document.raw_text
        assert "\n\n\n" not in document.raw_text
        assert "Text with multiple spaces" in document.raw_text
        assert "and newlines" in document.raw_text

    @pytest.mark.asyncio
    async def test_strips_headers_footers(
        self,
        ingestion_service: IngestionService,
        mock_pdf_extractor: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Removes page numbers, headers."""
        mock_pdf_extractor.extract.return_value = MockDocument(
            raw_text="Page 1 of 10\n\nActual content here.\n\n- 1 -\n\nMore content.",
            sections=[],
            metadata={},
        )

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        document = await ingestion_service.ingest_file(pdf_file)

        assert "Page 1 of 10" not in document.raw_text
        assert "- 1 -" not in document.raw_text
        assert "Actual content here" in document.raw_text
        assert "More content" in document.raw_text

    @pytest.mark.asyncio
    async def test_preserves_structure(
        self,
        ingestion_service: IngestionService,
        mock_text_loader: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Sections maintained after normalization."""
        from medanki.models.document import Section

        sections = [
            Section(title="Introduction", content="Intro text.", level=1, page_numbers=[1]),
            Section(title="Methods", content="Methods text.", level=1, page_numbers=[2]),
        ]
        mock_text_loader.load.return_value = MockDocument(
            raw_text="Full document text.",
            sections=sections,
            metadata={},
        )

        md_file = tmp_path / "test.md"
        md_file.write_text("# Introduction\n\nIntro text.\n\n# Methods\n\nMethods text.")

        document = await ingestion_service.ingest_file(md_file)

        assert len(document.sections) == 2
        assert document.sections[0].title == "Introduction"
        assert document.sections[1].title == "Methods"


class TestErrorHandling:
    """Tests for error handling functionality."""

    @pytest.mark.asyncio
    async def test_corrupted_file_raises(
        self,
        ingestion_service: IngestionService,
        mock_pdf_extractor: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Bad file raises IngestionError."""
        from medanki.ingestion.errors import IngestionError

        mock_pdf_extractor.extract.side_effect = Exception("Corrupted PDF")

        pdf_file = tmp_path / "corrupted.pdf"
        pdf_file.write_bytes(b"corrupted data")

        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.ingest_file(pdf_file)

        assert "corrupted" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_missing_file_raises(
        self,
        ingestion_service: IngestionService,
        tmp_path: Path,
    ) -> None:
        """FileNotFoundError wrapped."""
        from medanki.ingestion.errors import IngestionError

        missing_file = tmp_path / "nonexistent.pdf"

        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.ingest_file(missing_file)

        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_partial_failure_continues(
        self,
        ingestion_service: IngestionService,
        mock_pdf_extractor: AsyncMock,
        mock_text_loader: AsyncMock,
        temp_directory: Path,
    ) -> None:
        """One bad file doesn't stop batch."""
        call_count = 0
        original_extract = mock_pdf_extractor.extract

        async def extract_with_error(path: Path) -> MockDocument:
            nonlocal call_count
            call_count += 1
            if "document.pdf" in str(path):
                raise Exception("Corrupted file")
            return await original_extract(path)

        mock_pdf_extractor.extract = extract_with_error

        documents = await ingestion_service.ingest_directory(temp_directory)

        assert len(documents) == 4

    @pytest.mark.asyncio
    async def test_directory_not_found_raises(
        self,
        ingestion_service: IngestionService,
        tmp_path: Path,
    ) -> None:
        """Non-existent directory raises IngestionError."""
        from medanki.ingestion.errors import IngestionError

        missing_dir = tmp_path / "nonexistent_dir"

        with pytest.raises(IngestionError) as exc_info:
            await ingestion_service.ingest_directory(missing_dir)

        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()
