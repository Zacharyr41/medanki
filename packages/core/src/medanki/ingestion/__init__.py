"""Ingestion module for MedAnki."""

from medanki.ingestion.base import Document, Section, IngestionError, BaseExtractor, BaseLoader
from medanki.ingestion.errors import IngestionError
from medanki.ingestion.pdf import PDFExtractor
from medanki.ingestion.service import (
    IngestionService,
    IPDFExtractor,
    ITextLoader,
)
from medanki.ingestion.text import TextLoader, MarkdownLoader

__all__ = [
    "BaseExtractor",
    "BaseLoader",
    "Document",
    "IngestionError",
    "IngestionService",
    "IPDFExtractor",
    "ITextLoader",
    "MarkdownLoader",
    "PDFExtractor",
    "Section",
    "TextLoader",
]
