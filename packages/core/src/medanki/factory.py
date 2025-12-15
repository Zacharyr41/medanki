"""Service factory for MedAnki dependency injection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from medanki.generation.cloze import ClozeGenerator
    from medanki.generation.deduplicator import Deduplicator
    from medanki.generation.service import GenerationService
    from medanki.generation.validator import CardValidator
    from medanki.generation.vignette import VignetteGenerator
    from medanki.ingestion.service import IngestionService
    from medanki.processing.chunker import ChunkingService
    from medanki.processing.embedder import EmbeddingService
    from medanki.services.llm import ClaudeClient
    from medanki.services.taxonomy import TaxonomyService


@dataclass
class ServiceConfig:
    """Configuration for service factory."""

    anthropic_api_key: str | None = None
    taxonomy_dir: Path = Path("data/taxonomies")
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 75
    llm_model: str = "claude-sonnet-4-20250514"


class AsyncPDFExtractorAdapter:
    """Async adapter for the synchronous PDF extractor."""

    def __init__(self):
        from medanki.ingestion.pdf import PDFExtractor
        self._extractor = PDFExtractor()

    async def extract(self, path: Path):
        from medanki.models.document import Document as ServiceDocument
        from medanki.models.enums import ContentType

        result = self._extractor.extract(path)
        return ServiceDocument(
            source_path=path,
            content_type=ContentType.PDF_TEXTBOOK,
            raw_text=result.content,
            sections=[],
            metadata=result.metadata,
        )


class AsyncTextLoaderAdapter:
    """Async adapter for the synchronous text loaders."""

    def __init__(self):
        from medanki.ingestion.text import MarkdownLoader, TextLoader
        self._markdown_loader = MarkdownLoader()
        self._text_loader = TextLoader()

    async def load(self, path: Path):
        from medanki.models.document import Document as ServiceDocument
        from medanki.models.enums import ContentType

        suffix = path.suffix.lower()
        if suffix == ".md":
            result = self._markdown_loader.load(path)
            content_type = ContentType.MARKDOWN
        else:
            result = self._text_loader.load(path)
            content_type = ContentType.PLAIN_TEXT

        return ServiceDocument(
            source_path=path,
            content_type=content_type,
            raw_text=result.content,
            sections=[],
            metadata=result.metadata,
        )


class ServiceFactory:
    """Factory for creating and managing MedAnki services."""

    def __init__(self, config: ServiceConfig | None = None):
        self._config = config or ServiceConfig()
        self._llm_client: ClaudeClient | None = None
        self._taxonomy_service: TaxonomyService | None = None
        self._embedding_service: EmbeddingService | None = None
        self._chunking_service: ChunkingService | None = None
        self._ingestion_service: IngestionService | None = None

    @property
    def config(self) -> ServiceConfig:
        return self._config

    def get_llm_client(self) -> ClaudeClient:
        """Get or create LLM client."""
        if self._llm_client is None:
            from medanki.services.llm import ClaudeClient

            api_key = self._config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self._llm_client = ClaudeClient(api_key=api_key, model=self._config.llm_model)
        return self._llm_client

    def get_taxonomy_service(self) -> TaxonomyService:
        """Get or create taxonomy service."""
        if self._taxonomy_service is None:
            from medanki.services.taxonomy import TaxonomyService

            self._taxonomy_service = TaxonomyService(self._config.taxonomy_dir)
        return self._taxonomy_service

    def get_embedding_service(self) -> EmbeddingService:
        """Get or create embedding service."""
        if self._embedding_service is None:
            from medanki.processing.embedder import EmbeddingService

            self._embedding_service = EmbeddingService(
                model_name=self._config.embedding_model
            )
        return self._embedding_service

    def get_chunking_service(self) -> ChunkingService:
        """Get or create chunking service."""
        if self._chunking_service is None:
            from medanki.processing.chunker import ChunkingService

            self._chunking_service = ChunkingService(
                chunk_size=self._config.chunk_size,
                overlap=self._config.chunk_overlap,
            )
        return self._chunking_service

    def get_ingestion_service(self) -> IngestionService:
        """Get or create ingestion service."""
        if self._ingestion_service is None:
            from medanki.ingestion.service import IngestionService

            pdf_extractor = AsyncPDFExtractorAdapter()
            text_loader = AsyncTextLoaderAdapter()
            self._ingestion_service = IngestionService(
                pdf_extractor=pdf_extractor,
                text_loader=text_loader,
            )
        return self._ingestion_service

    def create_cloze_generator(self) -> ClozeGenerator:
        """Create a cloze card generator."""
        from medanki.generation.cloze import ClozeGenerator

        return ClozeGenerator(llm_client=self.get_llm_client())

    def create_vignette_generator(self) -> VignetteGenerator:
        """Create a vignette card generator."""
        from medanki.generation.vignette import VignetteGenerator

        return VignetteGenerator(llm_client=self.get_llm_client())

    def create_card_validator(self) -> CardValidator:
        """Create a card validator."""
        from medanki.generation.validator import CardValidator

        return CardValidator()

    def create_deduplicator(self) -> Deduplicator:
        """Create a card deduplicator."""
        from medanki.generation.deduplicator import Deduplicator

        return Deduplicator()

    def create_generation_service(self) -> GenerationService:
        """Create a fully wired generation service."""
        from medanki.generation.service import GenerationService

        class SimpleClassifier:
            async def classify_chunk(self, chunk):
                return "general"

        return GenerationService(
            cloze_generator=self.create_cloze_generator(),
            vignette_generator=self.create_vignette_generator(),
            validator=self.create_card_validator(),
            deduplicator=self.create_deduplicator(),
            classifier=SimpleClassifier(),
        )


_default_factory: ServiceFactory | None = None


def get_factory(config: ServiceConfig | None = None) -> ServiceFactory:
    """Get or create the default service factory."""
    global _default_factory
    if _default_factory is None or config is not None:
        _default_factory = ServiceFactory(config)
    return _default_factory
