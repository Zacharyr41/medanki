from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from medanki.models.cards import ClozeCard, VignetteCard


class DocumentType(Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"


class ChunkType(Enum):
    CONCEPT = "concept"
    PROCEDURE = "procedure"
    FACT = "fact"
    DEFINITION = "definition"
    CLINICAL_VIGNETTE = "clinical_vignette"


@dataclass
class Document:
    id: UUID
    path: Path
    content: str
    document_type: DocumentType
    metadata: dict[str, str | int | float | bool]


@dataclass
class Chunk:
    id: UUID
    document_id: UUID
    content: str
    chunk_type: ChunkType | None
    start_offset: int
    end_offset: int
    metadata: dict[str, str | int | float | bool]


@dataclass
class Embedding:
    chunk_id: UUID
    vector: list[float]
    model: str


@dataclass
class Topic:
    id: str
    name: str
    parent_id: str | None
    level: int
    metadata: dict[str, str | int | float | bool]


@dataclass
class SearchResult:
    chunk_id: UUID
    score: float
    chunk: Chunk


@dataclass
class ExportResult:
    path: Path
    card_count: int
    format: str


@runtime_checkable
class IIngestionService(Protocol):
    async def ingest_file(self, path: Path) -> Document:
        ...

    async def ingest_directory(
        self,
        path: Path,
        recursive: bool = True,
        extensions: Sequence[str] | None = None,
    ) -> list[Document]:
        ...


@runtime_checkable
class IChunkingService(Protocol):
    async def chunk_document(
        self,
        document: Document,
        max_chunk_size: int = 1000,
        overlap: int = 100,
    ) -> list[Chunk]:
        ...


@runtime_checkable
class IEmbeddingService(Protocol):
    @property
    def model_name(self) -> str:
        ...

    @property
    def embedding_dimension(self) -> int:
        ...

    async def embed(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        ...


@runtime_checkable
class IClassificationService(Protocol):
    async def classify_chunk(self, chunk: Chunk) -> ChunkType:
        ...


@runtime_checkable
class IGenerationService(Protocol):
    async def generate_cloze(
        self,
        chunk: Chunk,
        topic_id: str | None = None,
        max_cards: int = 3,
    ) -> list[ClozeCard]:
        ...

    async def generate_vignette(
        self,
        chunk: Chunk,
        topic_id: str | None = None,
    ) -> VignetteCard | None:
        ...


@runtime_checkable
class IValidationService(Protocol):
    async def validate_card(
        self,
        card: ClozeCard | VignetteCard,
    ) -> tuple[bool, list[str]]:
        ...


@runtime_checkable
class IExportService(Protocol):
    async def export_deck(
        self,
        cards: Sequence[ClozeCard | VignetteCard],
        output_path: Path,
        deck_name: str,
        format: str = "apkg",
    ) -> ExportResult:
        ...


@runtime_checkable
class IVectorStore(Protocol):
    async def upsert(
        self,
        embeddings: Sequence[Embedding],
        chunks: Sequence[Chunk],
    ) -> int:
        ...

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict[str, str | int | float | bool] | None = None,
    ) -> list[SearchResult]:
        ...

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        top_k: int = 10,
        alpha: float = 0.5,
        filter_metadata: dict[str, str | int | float | bool] | None = None,
    ) -> list[SearchResult]:
        ...


@runtime_checkable
class ITaxonomyService(Protocol):
    async def get_topics(
        self,
        parent_id: str | None = None,
        level: int | None = None,
    ) -> list[Topic]:
        ...

    async def search_topics(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Topic]:
        ...

    async def get_topic_by_id(self, topic_id: str) -> Topic | None:
        ...

    async def get_topic_ancestors(self, topic_id: str) -> list[Topic]:
        ...
