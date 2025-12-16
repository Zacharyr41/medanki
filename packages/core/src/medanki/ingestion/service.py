"""Ingestion service facade for MedAnki."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from medanki.ingestion.errors import IngestionError
from medanki.models.document import Document
from medanki.models.enums import ContentType

if TYPE_CHECKING:
    from collections.abc import Sequence


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".pptx"}

HEADER_FOOTER_PATTERNS = [
    re.compile(r"^Page\s+\d+\s+of\s+\d+\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*-\s*\d+\s*-\s*$", re.MULTILINE),
    re.compile(r"^\s*\d+\s*$", re.MULTILINE),
]

EXTENSION_TO_CONTENT_TYPE = {
    ".pdf": ContentType.PDF_TEXTBOOK,
    ".md": ContentType.MARKDOWN,
    ".txt": ContentType.PLAIN_TEXT,
    ".pptx": ContentType.POWERPOINT_SLIDES,
}


@runtime_checkable
class IPDFExtractor(Protocol):
    """Protocol for PDF extraction."""

    async def extract(self, path: Path) -> Document:
        """Extract content from a PDF file."""
        ...


@runtime_checkable
class ITextLoader(Protocol):
    """Protocol for text file loading."""

    async def load(self, path: Path) -> Document:
        """Load content from a text file."""
        ...


@runtime_checkable
class IPowerPointExtractor(Protocol):
    """Protocol for PowerPoint extraction."""

    async def extract(self, path: Path) -> Document:
        """Extract content from a PowerPoint file."""
        ...


class IngestionService:
    """Service facade for ingesting documents from various formats.

    Routes file processing to appropriate extractors based on file extension
    and applies normalization to extracted content.
    """

    def __init__(
        self,
        pdf_extractor: IPDFExtractor,
        text_loader: ITextLoader,
        powerpoint_extractor: IPowerPointExtractor | None = None,
    ) -> None:
        """Initialize the ingestion service.

        Args:
            pdf_extractor: Extractor for PDF files.
            text_loader: Loader for text and markdown files.
            powerpoint_extractor: Extractor for PowerPoint files (optional).
        """
        self._pdf_extractor = pdf_extractor
        self._text_loader = text_loader
        self._powerpoint_extractor = powerpoint_extractor

    async def ingest_file(self, path: Path) -> Document:
        """Ingest a single file and return a normalized Document.

        Args:
            path: Path to the file to ingest.

        Returns:
            Normalized Document object.

        Raises:
            IngestionError: If the file format is unsupported, file is missing,
                or extraction fails.
        """
        if not path.exists():
            raise IngestionError(
                f"File not found: {path}",
                path=str(path),
            )

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise IngestionError(
                f"Unsupported file format: {suffix}",
                path=str(path),
            )

        try:
            document = await self._extract_document(path)
        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError(
                f"Failed to extract content from {path}: {exc}",
                path=str(path),
            ) from exc

        return self._normalize_document(document, path)

    async def ingest_directory(
        self,
        path: Path,
        recursive: bool = True,
        extensions: Sequence[str] | None = None,
    ) -> list[Document]:
        """Ingest all supported files from a directory.

        Args:
            path: Path to the directory to process.
            recursive: Whether to recursively process subdirectories.
            extensions: Optional list of extensions to filter by.

        Returns:
            List of normalized Document objects.

        Raises:
            IngestionError: If the directory does not exist.
        """
        if not path.exists():
            raise IngestionError(
                f"Directory not found: {path}",
                path=str(path),
            )

        if not path.is_dir():
            raise IngestionError(
                f"Path is not a directory: {path}",
                path=str(path),
            )

        allowed_extensions = set(extensions) if extensions else SUPPORTED_EXTENSIONS

        files = self._collect_files(path, recursive, allowed_extensions)
        documents: list[Document] = []

        for file_path in files:
            try:
                document = await self.ingest_file(file_path)
                documents.append(document)
            except IngestionError:
                continue

        return documents

    def _collect_files(
        self,
        directory: Path,
        recursive: bool,
        extensions: set[str],
    ) -> list[Path]:
        """Collect files from directory matching the given extensions.

        Args:
            directory: Directory to search.
            recursive: Whether to search recursively.
            extensions: Set of allowed extensions.

        Returns:
            List of matching file paths.
        """
        files: list[Path] = []
        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            if file_path.name.startswith("."):
                continue

            if file_path.suffix.lower() in extensions:
                files.append(file_path)

        return sorted(files)

    async def _extract_document(self, path: Path) -> Document:
        """Route extraction to the appropriate extractor.

        Args:
            path: Path to the file.

        Returns:
            Extracted document.

        Raises:
            IngestionError: If no extractor is available for the file type.
        """
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return await self._pdf_extractor.extract(path)
        elif suffix == ".pptx":
            if self._powerpoint_extractor is None:
                from medanki.ingestion.powerpoint import PowerPointExtractor

                self._powerpoint_extractor = PowerPointExtractor()
            return await self._powerpoint_extractor.extract(path)
        else:
            return await self._text_loader.load(path)

    def _normalize_document(self, document: Document, path: Path) -> Document:
        """Normalize document content.

        Args:
            document: Document to normalize.
            path: Original file path.

        Returns:
            Normalized document.
        """
        raw_text = document.raw_text

        raw_text = self._strip_headers_footers(raw_text)
        raw_text = self._normalize_whitespace(raw_text)

        content_type = getattr(document, "content_type", None)
        if content_type is None:
            suffix = path.suffix.lower()
            content_type = EXTENSION_TO_CONTENT_TYPE.get(suffix, ContentType.PLAIN_TEXT)

        return Document(
            source_path=path,
            content_type=content_type,
            raw_text=raw_text,
            sections=document.sections,
            metadata=document.metadata,
        )

    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple whitespace characters.

        Args:
            text: Text to normalize.

        Returns:
            Text with normalized whitespace.
        """
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _strip_headers_footers(self, text: str) -> str:
        """Remove common header and footer patterns.

        Args:
            text: Text to clean.

        Returns:
            Text with headers/footers removed.
        """
        for pattern in HEADER_FOOTER_PATTERNS:
            text = pattern.sub("", text)
        return text
