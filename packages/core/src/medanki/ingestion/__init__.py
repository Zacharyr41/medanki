"""Ingestion module for MedAnki."""

from medanki.ingestion.base import BaseExtractor, BaseLoader, Document, Section
from medanki.ingestion.errors import IngestionError
from medanki.ingestion.pdf import PDFExtractor
from medanki.ingestion.service import (
    IngestionService,
    IPDFExtractor,
    ITextLoader,
)
from medanki.ingestion.text import MarkdownLoader, TextLoader

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
