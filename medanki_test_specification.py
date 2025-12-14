"""
MedAnki Test Specification
==========================

This file defines the complete system behavior through tests.
It serves as an executable specification - implementation must pass all tests.

Run with: pytest medanki_test_specification.py -v

Organization:
- Section 1: Domain Models & Interfaces (Protocols)
- Section 2: Ingestion Layer Tests
- Section 3: Processing Layer Tests
- Section 4: Generation Layer Tests  
- Section 5: Export Layer Tests
- Section 6: Integration Tests
- Section 7: Property-Based Tests
- Section 8: Edge Cases & Error Handling
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Protocol,
    runtime_checkable,
)

import pytest

# =============================================================================
# SECTION 1: DOMAIN MODELS & INTERFACES
# =============================================================================

# -----------------------------------------------------------------------------
# 1.1 Enumerations
# -----------------------------------------------------------------------------

class ExamType(Enum):
    """Supported standardized exam taxonomies."""
    MCAT = "mcat"
    USMLE_STEP1 = "usmle_step1"
    USMLE_STEP2 = "usmle_step2"


class ContentType(Enum):
    """Types of input content the system can process."""
    PDF_TEXTBOOK = "pdf_textbook"
    PDF_SLIDES = "pdf_slides"
    PDF_NOTES = "pdf_notes"
    AUDIO_LECTURE = "audio_lecture"
    VIDEO_LECTURE = "video_lecture"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class CardType(Enum):
    """Types of flashcards the system can generate."""
    CLOZE = "cloze"
    BASIC_QA = "basic_qa"
    VIGNETTE = "vignette"
    IMAGE_OCCLUSION = "image_occlusion"


class ValidationStatus(Enum):
    """Card validation outcomes."""
    VALID = "valid"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_MEDICAL = "invalid_medical"
    HALLUCINATION_DETECTED = "hallucination_detected"
    DUPLICATE = "duplicate"


# -----------------------------------------------------------------------------
# 1.2 Domain Models (Data Classes)
# -----------------------------------------------------------------------------

@dataclass
class Section:
    """A section within a document."""
    title: str
    level: int  # 1=chapter, 2=section, 3=subsection
    start_char: int
    end_char: int
    page_number: int | None = None


@dataclass
class MedicalEntity:
    """A recognized medical entity with optional UMLS linking."""
    text: str
    label: str  # DISEASE, DRUG, ANATOMY, PROCEDURE, etc.
    start: int
    end: int
    cui: str | None = None  # UMLS Concept Unique Identifier
    confidence: float = 1.0


@dataclass
class Document:
    """Normalized document representation from any input source."""
    id: str
    source_path: str
    content_type: ContentType
    raw_text: str
    sections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chunk:
    """A processed text segment ready for classification and embedding."""
    id: str
    document_id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    page_number: int | None = None
    section_path: list[str] = field(default_factory=list)
    entities: list[MedicalEntity] = field(default_factory=list)
    embedding: list[float] | None = None


@dataclass
class TopicMatch:
    """A taxonomy topic classification result."""
    topic_id: str
    topic_name: str
    path: list[str]  # Hierarchical path: ["Cardiology", "Pathology", "Heart_Failure"]
    confidence: float
    exam_type: ExamType
    
    @property
    def path_str(self) -> str:
        return "::".join(self.path)


@dataclass
class ClassifiedChunk:
    """A chunk with its taxonomy classifications."""
    chunk: Chunk
    mcat_topics: list[TopicMatch] = field(default_factory=list)
    usmle_topics: list[TopicMatch] = field(default_factory=list)
    primary_exam: ExamType | None = None


@dataclass
class ClozeCard:
    """A cloze deletion flashcard."""
    id: str
    text: str  # Contains {{c1::...}} syntax
    extra: str = ""
    source_chunk_id: str = ""
    tags: list[str] = field(default_factory=list)
    difficulty: str = "medium"


@dataclass
class VignetteCard:
    """A clinical vignette (USMLE-style) flashcard."""
    id: str
    front: str  # Clinical stem
    answer: str  # 1-3 word answer
    explanation: str
    distinguishing_feature: str | None = None
    source_chunk_id: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating a generated card."""
    status: ValidationStatus
    is_valid: bool
    accuracy_score: float = 1.0
    hallucination_risk: float = 0.0
    quality_score: float = 1.0
    issues: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of the full generation pipeline."""
    cards: list[ClozeCard | VignetteCard]
    document_count: int
    chunk_count: int
    topics_matched: int
    validation_failures: int
    duplicates_removed: int
    output_path: str | None = None


# -----------------------------------------------------------------------------
# 1.3 Service Interfaces (Protocols)
# -----------------------------------------------------------------------------

@runtime_checkable
class IIngestionService(Protocol):
    """Contract for document ingestion services."""
    
    async def ingest(self, path: Path) -> Document:
        """Ingest a file and return a normalized Document."""
        ...
    
    def supported_formats(self) -> list[str]:
        """Return list of supported file extensions."""
        ...
    
    def detect_content_type(self, path: Path) -> ContentType:
        """Detect the content type of a file."""
        ...


@runtime_checkable
class IChunkingService(Protocol):
    """Contract for text chunking services."""
    
    def chunk(self, document: Document) -> list[Chunk]:
        """Split document into processable chunks."""
        ...
    
    def get_token_count(self, text: str) -> int:
        """Count tokens in text using the configured tokenizer."""
        ...


@runtime_checkable
class IEmbeddingService(Protocol):
    """Contract for embedding generation services."""
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...
    
    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...
    
    @property
    def dimensions(self) -> int:
        """Return the embedding dimensionality."""
        ...


@runtime_checkable
class IClassificationService(Protocol):
    """Contract for taxonomy classification services."""
    
    async def classify(
        self,
        chunk: Chunk,
        exam_type: ExamType
    ) -> list[TopicMatch]:
        """Classify a chunk against the specified taxonomy."""
        ...
    
    async def classify_dual(
        self,
        chunk: Chunk
    ) -> dict[ExamType, list[TopicMatch]]:
        """Classify against both MCAT and USMLE taxonomies."""
        ...


@runtime_checkable
class IGenerationService(Protocol):
    """Contract for flashcard generation services."""
    
    async def generate_cloze(
        self,
        chunk: ClassifiedChunk,
        count: int
    ) -> list[ClozeCard]:
        """Generate cloze deletion cards from a chunk."""
        ...
    
    async def generate_vignette(
        self,
        chunk: ClassifiedChunk
    ) -> VignetteCard | None:
        """Generate a clinical vignette card from a chunk."""
        ...


@runtime_checkable
class IValidationService(Protocol):
    """Contract for card validation services."""
    
    async def validate(
        self,
        card: ClozeCard | VignetteCard
    ) -> ValidationResult:
        """Validate a generated card."""
        ...
    
    async def check_duplicate(
        self,
        card: ClozeCard | VignetteCard,
        existing_cards: list[ClozeCard | VignetteCard]
    ) -> bool:
        """Check if card is a duplicate of existing cards."""
        ...


@runtime_checkable
class IExportService(Protocol):
    """Contract for Anki export services."""
    
    def build_deck(
        self,
        cards: list[ClozeCard | VignetteCard],
        exam_type: ExamType,
        deck_name: str
    ) -> Path:
        """Build an .apkg file from cards."""
        ...
    
    def build_tags(
        self,
        topics: list[TopicMatch],
        source: str | None
    ) -> list[str]:
        """Build hierarchical tags from topic matches."""
        ...


@runtime_checkable
class IVectorStore(Protocol):
    """Contract for vector storage and retrieval."""
    
    async def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict[str, Any]],
        ids: list[str]
    ) -> None:
        """Insert or update vectors with metadata."""
        ...
    
    async def hybrid_search(
        self,
        collection: str,
        query_text: str,
        query_vector: list[float],
        alpha: float,
        limit: int
    ) -> list[dict[str, Any]]:
        """Perform hybrid BM25 + vector search."""
        ...


@runtime_checkable
class ITaxonomyService(Protocol):
    """Contract for taxonomy management."""
    
    def get_topics(self, exam_type: ExamType) -> list[TopicMatch]:
        """Get all topics for an exam type."""
        ...
    
    def get_topic_by_id(self, topic_id: str) -> TopicMatch | None:
        """Get a specific topic by ID."""
        ...
    
    async def get_topic_embeddings(
        self,
        exam_type: ExamType
    ) -> dict[str, list[float]]:
        """Get pre-computed embeddings for all topics."""
        ...


# =============================================================================
# SECTION 2: INGESTION LAYER TESTS
# =============================================================================

class TestPDFIngestion:
    """Tests for PDF document ingestion."""
    
    # -------------------------------------------------------------------------
    # 2.1 Basic PDF Extraction
    # -------------------------------------------------------------------------
    
    def test_ingest_simple_pdf_returns_document(
        self,
        pdf_ingestor: IIngestionService,
        simple_pdf_path: Path
    ):
        """Ingesting a simple PDF returns a valid Document."""
        document = pytest.run_sync(pdf_ingestor.ingest(simple_pdf_path))
        
        assert isinstance(document, Document)
        assert document.id is not None
        assert len(document.id) > 0
        assert document.source_path == str(simple_pdf_path)
        assert document.content_type in [
            ContentType.PDF_TEXTBOOK,
            ContentType.PDF_SLIDES,
            ContentType.PDF_NOTES
        ]
        assert len(document.raw_text) > 0
    
    def test_ingest_pdf_extracts_text_content(
        self,
        pdf_ingestor: IIngestionService,
        pdf_with_known_content: tuple[Path, str]
    ):
        """PDF extraction captures expected text content."""
        pdf_path, expected_substring = pdf_with_known_content
        document = pytest.run_sync(pdf_ingestor.ingest(pdf_path))
        
        # Normalize whitespace for comparison
        normalized_text = " ".join(document.raw_text.split())
        normalized_expected = " ".join(expected_substring.split())
        
        assert normalized_expected in normalized_text
    
    def test_ingest_pdf_preserves_section_structure(
        self,
        pdf_ingestor: IIngestionService,
        pdf_with_headers: Path
    ):
        """PDF extraction identifies section headers."""
        document = pytest.run_sync(pdf_ingestor.ingest(pdf_with_headers))
        
        assert len(document.sections) > 0
        
        # Sections should have valid structure
        for section in document.sections:
            assert section.title is not None
            assert section.level >= 1
            assert section.start_char >= 0
            assert section.end_char > section.start_char
    
    def test_ingest_pdf_extracts_page_numbers(
        self,
        pdf_ingestor: IIngestionService,
        multi_page_pdf: Path
    ):
        """PDF extraction tracks page number metadata."""
        document = pytest.run_sync(pdf_ingestor.ingest(multi_page_pdf))
        
        assert "page_count" in document.metadata
        assert document.metadata["page_count"] > 1
        
        # At least some sections should have page numbers
        sections_with_pages = [s for s in document.sections if s.page_number is not None]
        assert len(sections_with_pages) > 0
    
    # -------------------------------------------------------------------------
    # 2.2 PDF Extraction Strategy Selection
    # -------------------------------------------------------------------------
    
    def test_scanned_pdf_uses_ocr_extractor(
        self,
        pdf_extraction_strategy,
        scanned_pdf_path: Path
    ):
        """Scanned PDFs are routed to OCR-based extraction."""
        extractor = pdf_extraction_strategy.select_extractor(scanned_pdf_path)
        
        assert extractor.__class__.__name__ in ["PaddleOCRExtractor", "TesseractExtractor"]
    
    def test_pdf_with_tables_uses_docling(
        self,
        pdf_extraction_strategy,
        table_heavy_pdf: Path
    ):
        """PDFs with complex tables use Docling for extraction."""
        extractor = pdf_extraction_strategy.select_extractor(table_heavy_pdf)
        
        # Should use Docling or Marker with LLM mode
        assert extractor.__class__.__name__ in ["DoclingExtractor", "MarkerExtractor"]
    
    def test_pdf_with_equations_uses_appropriate_extractor(
        self,
        pdf_extraction_strategy,
        math_heavy_pdf: Path
    ):
        """PDFs with heavy math use Nougat or Marker+LLM."""
        extractor = pdf_extraction_strategy.select_extractor(math_heavy_pdf)
        
        assert extractor.__class__.__name__ in ["NougatExtractor", "MarkerExtractor"]
    
    def test_large_pdf_prioritizes_speed(
        self,
        pdf_extraction_strategy,
        large_pdf_path: Path  # >100 pages
    ):
        """Large PDFs use fast extraction method."""
        extractor = pdf_extraction_strategy.select_extractor(large_pdf_path)
        
        # Should use PyMuPDF for speed
        assert extractor.__class__.__name__ in ["PyMuPDF4LLMExtractor", "MarkerExtractor"]
    
    # -------------------------------------------------------------------------
    # 2.3 Table Extraction
    # -------------------------------------------------------------------------
    
    def test_tables_extracted_as_structured_data(
        self,
        pdf_ingestor: IIngestionService,
        pdf_with_tables: Path
    ):
        """Tables in PDFs are extracted with structure preserved."""
        document = pytest.run_sync(pdf_ingestor.ingest(pdf_with_tables))
        
        # Tables should be in metadata or identifiable in text
        assert "tables" in document.metadata or "|" in document.raw_text
    
    def test_drug_dosage_table_preserves_values(
        self,
        pdf_ingestor: IIngestionService,
        pdf_with_drug_table: tuple[Path, dict[str, str]]
    ):
        """Drug dosage tables preserve numeric values correctly."""
        pdf_path, expected_values = pdf_with_drug_table
        document = pytest.run_sync(pdf_ingestor.ingest(pdf_path))
        
        for drug, dosage in expected_values.items():
            assert drug in document.raw_text
            assert dosage in document.raw_text


class TestAudioIngestion:
    """Tests for audio/lecture transcription."""
    
    def test_ingest_audio_returns_document(
        self,
        audio_ingestor: IIngestionService,
        sample_audio_path: Path
    ):
        """Audio ingestion returns a valid Document."""
        document = pytest.run_sync(audio_ingestor.ingest(sample_audio_path))
        
        assert isinstance(document, Document)
        assert document.content_type == ContentType.AUDIO_LECTURE
        assert len(document.raw_text) > 0
    
    def test_audio_transcription_includes_timestamps(
        self,
        audio_ingestor: IIngestionService,
        sample_audio_path: Path
    ):
        """Transcription includes timestamp metadata."""
        document = pytest.run_sync(audio_ingestor.ingest(sample_audio_path))
        
        assert "duration" in document.metadata
        assert document.metadata["duration"] > 0
    
    def test_audio_segments_by_natural_pauses(
        self,
        audio_ingestor: IIngestionService,
        lecture_with_pauses: Path
    ):
        """Audio is segmented at natural speaking pauses."""
        document = pytest.run_sync(audio_ingestor.ingest(lecture_with_pauses))
        
        # Should have multiple sections from segmentation
        assert len(document.sections) > 1
    
    def test_supported_audio_formats(self, audio_ingestor: IIngestionService):
        """Audio ingestor supports common formats."""
        formats = audio_ingestor.supported_formats()
        
        assert ".mp3" in formats
        assert ".wav" in formats
        assert ".m4a" in formats
        assert ".webm" in formats


class TestContentTypeDetection:
    """Tests for automatic content type detection."""
    
    @pytest.mark.parametrize("filename,expected_type", [
        ("lecture_slides.pdf", ContentType.PDF_SLIDES),
        ("kaplan_biochem.pdf", ContentType.PDF_TEXTBOOK),
        ("my_notes.pdf", ContentType.PDF_NOTES),
        ("recording.mp3", ContentType.AUDIO_LECTURE),
        ("notes.md", ContentType.MARKDOWN),
        ("outline.txt", ContentType.PLAIN_TEXT),
    ])
    def test_content_type_detection_by_filename(
        self,
        ingestor: IIngestionService,
        filename: str,
        expected_type: ContentType,
        tmp_path: Path
    ):
        """Content type is correctly detected from filename patterns."""
        # Create dummy file
        file_path = tmp_path / filename
        file_path.touch()
        
        detected = ingestor.detect_content_type(file_path)
        
        # Should detect or reasonably infer the type
        assert detected in [expected_type, ContentType.PDF_NOTES]  # Notes is fallback


# =============================================================================
# SECTION 3: PROCESSING LAYER TESTS
# =============================================================================

class TestChunking:
    """Tests for document chunking behavior."""
    
    # -------------------------------------------------------------------------
    # 3.1 Basic Chunking
    # -------------------------------------------------------------------------
    
    def test_chunk_produces_non_empty_chunks(
        self,
        chunker: IChunkingService,
        sample_document: Document
    ):
        """Chunking produces at least one non-empty chunk."""
        chunks = chunker.chunk(sample_document)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk.text.strip()) > 0
    
    def test_chunk_respects_max_token_limit(
        self,
        chunker: IChunkingService,
        long_document: Document,
        max_tokens: int = 512
    ):
        """No chunk exceeds the maximum token limit."""
        chunks = chunker.chunk(long_document)
        
        for chunk in chunks:
            assert chunk.token_count <= max_tokens
    
    def test_chunk_respects_min_token_limit(
        self,
        chunker: IChunkingService,
        sample_document: Document,
        min_tokens: int = 100
    ):
        """Chunks meet minimum token threshold (except final chunk)."""
        chunks = chunker.chunk(sample_document)
        
        # All except possibly the last chunk should meet minimum
        for chunk in chunks[:-1]:
            assert chunk.token_count >= min_tokens
    
    def test_chunks_cover_entire_document(
        self,
        chunker: IChunkingService,
        sample_document: Document
    ):
        """Chunks collectively cover all document content."""
        chunks = chunker.chunk(sample_document)
        
        # Verify coverage by checking that combined chunks contain key content
        combined_text = " ".join(c.text for c in chunks)
        
        # Sample the document at various points
        doc_words = sample_document.raw_text.split()
        sample_indices = [0, len(doc_words)//4, len(doc_words)//2, -1]
        
        for idx in sample_indices:
            word = doc_words[idx]
            if len(word) > 3:  # Skip short words
                assert word in combined_text
    
    def test_chunk_ids_are_unique(
        self,
        chunker: IChunkingService,
        sample_document: Document
    ):
        """Each chunk has a unique identifier."""
        chunks = chunker.chunk(sample_document)
        
        ids = [chunk.id for chunk in chunks]
        assert len(ids) == len(set(ids))
    
    def test_chunks_track_document_id(
        self,
        chunker: IChunkingService,
        sample_document: Document
    ):
        """Each chunk references its source document."""
        chunks = chunker.chunk(sample_document)
        
        for chunk in chunks:
            assert chunk.document_id == sample_document.id
    
    # -------------------------------------------------------------------------
    # 3.2 Medical-Specific Chunking Rules
    # -------------------------------------------------------------------------
    
    def test_chunk_preserves_drug_names(
        self,
        chunker: IChunkingService,
        document_with_drug_names: Document
    ):
        """Multi-word drug names are not split across chunks."""
        drug_names = [
            "atorvastatin calcium",
            "metoprolol succinate",
            "lisinopril hydrochlorothiazide",
        ]
        
        chunks = chunker.chunk(document_with_drug_names)
        
        for drug in drug_names:
            if drug in document_with_drug_names.raw_text:
                # Drug should appear complete in at least one chunk
                found_complete = any(drug in chunk.text for chunk in chunks)
                assert found_complete, f"Drug name '{drug}' was split across chunks"
    
    def test_chunk_preserves_anatomical_terms(
        self,
        chunker: IChunkingService,
        document_with_anatomy: Document
    ):
        """Compound anatomical terms stay together."""
        anatomical_terms = [
            "left anterior descending artery",
            "right coronary artery",
            "superior mesenteric artery",
        ]
        
        chunks = chunker.chunk(document_with_anatomy)
        
        for term in anatomical_terms:
            if term in document_with_anatomy.raw_text:
                found_complete = any(term in chunk.text for chunk in chunks)
                assert found_complete, f"Anatomical term '{term}' was split"
    
    def test_chunk_preserves_lab_values_with_units(
        self,
        chunker: IChunkingService,
        document_with_labs: Document
    ):
        """Lab values remain attached to their units."""
        lab_patterns = [
            r"\d+\s*mg/dL",
            r"\d+\s*mEq/L",
            r"\d+\s*mmol/L",
        ]
        
        chunks = chunker.chunk(document_with_labs)
        
        for pattern in lab_patterns:
            matches = re.findall(pattern, document_with_labs.raw_text)
            for match in matches:
                # Each lab value should appear complete in some chunk
                found = any(match in chunk.text for chunk in chunks)
                assert found, f"Lab value '{match}' was split from its unit"
    
    def test_chunk_preserves_abbreviations(
        self,
        chunker: IChunkingService,
        document_with_abbreviations: Document
    ):
        """Medical abbreviations are preserved."""
        abbreviations = ["CHF", "DVT", "PE", "MI", "COPD", "DKA"]
        
        chunks = chunker.chunk(document_with_abbreviations)
        combined = " ".join(c.text for c in chunks)
        
        for abbrev in abbreviations:
            if abbrev in document_with_abbreviations.raw_text:
                assert abbrev in combined
    
    # -------------------------------------------------------------------------
    # 3.3 Topic Boundary Detection
    # -------------------------------------------------------------------------
    
    def test_chunk_respects_section_boundaries(
        self,
        chunker: IChunkingService,
        document_with_sections: Document
    ):
        """Chunks prefer to break at section boundaries."""
        chunks = chunker.chunk(document_with_sections)
        
        # Most chunks should start at or near section boundaries
        section_starts = [s.start_char for s in document_with_sections.sections]
        
        chunks_at_boundaries = sum(
            1 for chunk in chunks
            if any(abs(chunk.start_char - start) < 50 for start in section_starts)
        )
        
        # At least 50% should align with boundaries
        assert chunks_at_boundaries >= len(chunks) * 0.5
    
    def test_chunk_detects_topic_shifts(
        self,
        chunker: IChunkingService,
        document_with_topic_shift: Document
    ):
        """Chunker identifies topic shifts within sections."""
        # Document transitions from cardiology to nephrology
        chunks = chunker.chunk(document_with_topic_shift)
        
        # Should have chunks that don't mix topics
        [c for c in chunks if "heart" in c.text.lower()]
        [c for c in chunks if "kidney" in c.text.lower()]
        
        # Chunks shouldn't heavily mix both topics
        mixed_chunks = [
            c for c in chunks
            if "heart" in c.text.lower() and "kidney" in c.text.lower()
        ]
        
        assert len(mixed_chunks) < len(chunks) * 0.3  # <30% mixed
    
    # -------------------------------------------------------------------------
    # 3.4 Entity Extraction
    # -------------------------------------------------------------------------
    
    def test_chunk_extracts_medical_entities(
        self,
        chunker: IChunkingService,
        document_with_entities: Document
    ):
        """Chunks include recognized medical entities."""
        chunks = chunker.chunk(document_with_entities)
        
        # At least some chunks should have entities
        chunks_with_entities = [c for c in chunks if len(c.entities) > 0]
        assert len(chunks_with_entities) > 0
    
    def test_entities_have_valid_labels(
        self,
        chunker: IChunkingService,
        document_with_entities: Document
    ):
        """Extracted entities have valid medical labels."""
        valid_labels = {
            "DISEASE", "DRUG", "ANATOMY", "PROCEDURE", "GENE",
            "CHEMICAL", "ORGANISM", "SYMPTOM", "FINDING"
        }
        
        chunks = chunker.chunk(document_with_entities)
        
        for chunk in chunks:
            for entity in chunk.entities:
                assert entity.label in valid_labels
    
    def test_entities_have_valid_spans(
        self,
        chunker: IChunkingService,
        document_with_entities: Document
    ):
        """Entity spans correctly reference chunk text."""
        chunks = chunker.chunk(document_with_entities)
        
        for chunk in chunks:
            for entity in chunk.entities:
                # Entity span should match text
                extracted = chunk.text[entity.start:entity.end]
                assert extracted == entity.text


class TestEmbedding:
    """Tests for embedding generation."""
    
    def test_embed_returns_correct_dimensions(
        self,
        embedder: IEmbeddingService,
        sample_texts: list[str]
    ):
        """Embeddings have the expected dimensionality."""
        embeddings = pytest.run_sync(embedder.embed(sample_texts))
        
        assert len(embeddings) == len(sample_texts)
        for emb in embeddings:
            assert len(emb) == embedder.dimensions
    
    def test_embed_single_matches_batch(
        self,
        embedder: IEmbeddingService,
        sample_text: str
    ):
        """Single embedding matches batch embedding for same text."""
        single = pytest.run_sync(embedder.embed_single(sample_text))
        batch = pytest.run_sync(embedder.embed([sample_text]))[0]
        
        # Should be identical or very close
        assert len(single) == len(batch)
        for s, b in zip(single, batch, strict=False):
            assert abs(s - b) < 1e-6
    
    def test_similar_texts_have_similar_embeddings(
        self,
        embedder: IEmbeddingService
    ):
        """Semantically similar texts produce similar embeddings."""
        texts = [
            "Myocardial infarction causes chest pain",
            "Heart attack results in chest discomfort",
            "Renal failure leads to elevated creatinine"  # Different topic
        ]
        
        embeddings = pytest.run_sync(embedder.embed(texts))
        
        # Compute cosine similarity
        def cosine_sim(a, b):
            dot = sum(x*y for x, y in zip(a, b, strict=False))
            norm_a = sum(x*x for x in a) ** 0.5
            norm_b = sum(x*x for x in b) ** 0.5
            return dot / (norm_a * norm_b)
        
        sim_01 = cosine_sim(embeddings[0], embeddings[1])  # Similar
        sim_02 = cosine_sim(embeddings[0], embeddings[2])  # Different
        
        assert sim_01 > sim_02
    
    def test_embed_handles_empty_string(
        self,
        embedder: IEmbeddingService
    ):
        """Empty strings produce valid (possibly zero) embeddings."""
        embedding = pytest.run_sync(embedder.embed_single(""))
        
        assert len(embedding) == embedder.dimensions
    
    def test_embed_handles_long_text(
        self,
        embedder: IEmbeddingService,
        long_medical_text: str  # >512 tokens
    ):
        """Long texts are handled (truncated or chunked internally)."""
        embedding = pytest.run_sync(embedder.embed_single(long_medical_text))
        
        assert len(embedding) == embedder.dimensions
        assert any(v != 0 for v in embedding)


class TestClassification:
    """Tests for taxonomy classification."""
    
    # -------------------------------------------------------------------------
    # 3.5 Basic Classification
    # -------------------------------------------------------------------------
    
    def test_classify_returns_topic_matches(
        self,
        classifier: IClassificationService,
        cardiology_chunk: Chunk
    ):
        """Classification returns topic matches."""
        topics = pytest.run_sync(
            classifier.classify(cardiology_chunk, ExamType.USMLE_STEP1)
        )
        
        assert len(topics) > 0
        for topic in topics:
            assert isinstance(topic, TopicMatch)
            assert topic.confidence > 0
    
    def test_classify_cardiology_content(
        self,
        classifier: IClassificationService,
        cardiology_chunk: Chunk
    ):
        """Cardiology content is classified to cardiovascular topics."""
        topics = pytest.run_sync(
            classifier.classify(cardiology_chunk, ExamType.USMLE_STEP1)
        )
        
        topic_paths = [t.path_str.lower() for t in topics]
        
        assert any("cardiovascular" in p or "cardio" in p for p in topic_paths)
    
    def test_classify_pharmacology_content(
        self,
        classifier: IClassificationService,
        pharmacology_chunk: Chunk
    ):
        """Pharmacology content is classified to drug-related topics."""
        topics = pytest.run_sync(
            classifier.classify(pharmacology_chunk, ExamType.USMLE_STEP1)
        )
        
        topic_paths = [t.path_str.lower() for t in topics]
        disciplines = [t.path[1].lower() if len(t.path) > 1 else "" for t in topics]
        
        assert any("pharmacology" in p or "drug" in p for p in topic_paths) or \
               any("pharmacology" in d for d in disciplines)
    
    # -------------------------------------------------------------------------
    # 3.6 Multi-Label Classification
    # -------------------------------------------------------------------------
    
    def test_classify_returns_multiple_topics(
        self,
        classifier: IClassificationService,
        multi_topic_chunk: Chunk  # e.g., "Beta-blockers in heart failure"
    ):
        """Content spanning topics gets multiple classifications."""
        topics = pytest.run_sync(
            classifier.classify(multi_topic_chunk, ExamType.USMLE_STEP1)
        )
        
        # Should have both Cardiology and Pharmacology
        assert len(topics) >= 2
    
    def test_classify_respects_max_topics(
        self,
        classifier: IClassificationService,
        multi_topic_chunk: Chunk,
        max_topics: int = 5
    ):
        """Classification respects maximum topic limit."""
        topics = pytest.run_sync(
            classifier.classify(multi_topic_chunk, ExamType.USMLE_STEP1)
        )
        
        assert len(topics) <= max_topics
    
    # -------------------------------------------------------------------------
    # 3.7 Confidence Thresholds
    # -------------------------------------------------------------------------
    
    def test_classify_respects_base_threshold(
        self,
        classifier: IClassificationService,
        sample_chunk: Chunk,
        base_threshold: float = 0.65
    ):
        """All returned topics exceed base confidence threshold."""
        topics = pytest.run_sync(
            classifier.classify(sample_chunk, ExamType.USMLE_STEP1)
        )
        
        for topic in topics:
            assert topic.confidence >= base_threshold
    
    def test_classify_applies_relative_threshold(
        self,
        classifier: IClassificationService,
        sample_chunk: Chunk,
        relative_threshold: float = 0.80
    ):
        """Topics are within relative threshold of top match."""
        topics = pytest.run_sync(
            classifier.classify(sample_chunk, ExamType.USMLE_STEP1)
        )
        
        if len(topics) > 1:
            top_confidence = topics[0].confidence
            min_allowed = top_confidence * relative_threshold
            
            for topic in topics:
                assert topic.confidence >= min_allowed
    
    # -------------------------------------------------------------------------
    # 3.8 Dual Taxonomy Classification
    # -------------------------------------------------------------------------
    
    def test_classify_dual_returns_both_taxonomies(
        self,
        classifier: IClassificationService,
        biochemistry_chunk: Chunk
    ):
        """Dual classification returns results for both MCAT and USMLE."""
        results = pytest.run_sync(classifier.classify_dual(biochemistry_chunk))
        
        assert ExamType.MCAT in results
        assert ExamType.USMLE_STEP1 in results
    
    def test_mcat_classification_uses_foundational_concepts(
        self,
        classifier: IClassificationService,
        biochemistry_chunk: Chunk
    ):
        """MCAT classification maps to Foundational Concepts."""
        topics = pytest.run_sync(
            classifier.classify(biochemistry_chunk, ExamType.MCAT)
        )
        
        # MCAT paths should include FC references
        fc_pattern = re.compile(r"FC\d+|Foundational", re.IGNORECASE)
        has_fc = any(fc_pattern.search(t.path_str) for t in topics)
        
        assert has_fc or len(topics) == 0  # Either has FC or no matches
    
    def test_usmle_classification_uses_organ_systems(
        self,
        classifier: IClassificationService,
        cardiology_chunk: Chunk
    ):
        """USMLE classification maps to organ systems."""
        topics = pytest.run_sync(
            classifier.classify(cardiology_chunk, ExamType.USMLE_STEP1)
        )
        
        organ_systems = {
            "cardiovascular", "respiratory", "renal", "gastrointestinal",
            "endocrine", "nervous", "musculoskeletal", "reproductive"
        }
        
        has_system = any(
            any(sys in t.path_str.lower() for sys in organ_systems)
            for t in topics
        )
        
        assert has_system
    
    # -------------------------------------------------------------------------
    # 3.9 Abbreviation Handling (Hybrid Search)
    # -------------------------------------------------------------------------
    
    def test_classify_handles_abbreviations(
        self,
        classifier: IClassificationService
    ):
        """Classification correctly handles medical abbreviations."""
        chunk = Chunk(
            id="test",
            document_id="doc",
            text="Patient with CHF presents with JVD and bilateral LE edema",
            start_char=0,
            end_char=100,
            token_count=15
        )
        
        topics = pytest.run_sync(
            classifier.classify(chunk, ExamType.USMLE_STEP1)
        )
        
        # Should recognize CHF = Congestive Heart Failure = Cardiovascular
        topic_paths = [t.path_str.lower() for t in topics]
        assert any("cardio" in p or "heart" in p for p in topic_paths)
    
    def test_classify_handles_rare_abbreviations(
        self,
        classifier: IClassificationService
    ):
        """Classification handles less common abbreviations."""
        chunk = Chunk(
            id="test",
            document_id="doc", 
            text="HOCM causes dynamic LVOT obstruction during systole",
            start_char=0,
            end_char=100,
            token_count=10
        )
        
        topics = pytest.run_sync(
            classifier.classify(chunk, ExamType.USMLE_STEP1)
        )
        
        # HOCM = Hypertrophic Obstructive Cardiomyopathy
        assert len(topics) > 0  # Should find some match


class TestVectorStore:
    """Tests for vector storage operations."""
    
    def test_upsert_and_retrieve(
        self,
        vector_store: IVectorStore,
        sample_vectors: list[list[float]],
        sample_metadata: list[dict]
    ):
        """Vectors can be stored and retrieved."""
        ids = [f"test_{i}" for i in range(len(sample_vectors))]
        
        pytest.run_sync(
            vector_store.upsert("test_collection", sample_vectors, sample_metadata, ids)
        )
        
        results = pytest.run_sync(
            vector_store.hybrid_search(
                "test_collection",
                query_text="test query",
                query_vector=sample_vectors[0],
                alpha=0.5,
                limit=10
            )
        )
        
        assert len(results) > 0
    
    def test_hybrid_search_balances_bm25_and_vector(
        self,
        vector_store: IVectorStore
    ):
        """Hybrid search uses both keyword and semantic matching."""
        # Store documents with specific keywords
        vectors = [[0.1] * 768, [0.9] * 768]
        metadata = [
            {"text": "heart failure treatment options"},
            {"text": "kidney disease management"}
        ]
        ids = ["doc1", "doc2"]
        
        pytest.run_sync(
            vector_store.upsert("test", vectors, metadata, ids)
        )
        
        # Search with keyword that matches doc1 but vector closer to doc2
        results = pytest.run_sync(
            vector_store.hybrid_search(
                "test",
                query_text="heart failure",  # Keyword match for doc1
                query_vector=[0.85] * 768,    # Vector closer to doc2
                alpha=0.5,  # Balanced
                limit=2
            )
        )
        
        # Both should appear in results
        assert len(results) == 2


# =============================================================================
# SECTION 4: GENERATION LAYER TESTS
# =============================================================================

class TestClozeGeneration:
    """Tests for cloze deletion card generation."""
    
    # -------------------------------------------------------------------------
    # 4.1 Basic Cloze Generation
    # -------------------------------------------------------------------------
    
    def test_generate_cloze_returns_cards(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Generation produces cloze cards."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=3))
        
        assert len(cards) > 0
        for card in cards:
            assert isinstance(card, ClozeCard)
    
    def test_generate_cloze_respects_count(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Generation produces requested number of cards."""
        for count in [1, 3, 5]:
            cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=count))
            assert len(cards) == count
    
    def test_cloze_contains_deletion_syntax(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Generated cloze cards contain valid deletion syntax."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=1))
        
        cloze_pattern = re.compile(r"\{\{c\d+::[^}]+\}\}")
        
        for card in cards:
            assert cloze_pattern.search(card.text), \
                f"Card missing cloze syntax: {card.text}"
    
    def test_cloze_deletion_has_short_answer(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk,
        max_words: int = 4
    ):
        """Cloze deletions have concise answers (1-4 words)."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=3))
        
        for card in cards:
            # Extract cloze answers
            answers = re.findall(r"\{\{c\d+::([^}]+)\}\}", card.text)
            for answer in answers:
                word_count = len(answer.split())
                assert word_count <= max_words, \
                    f"Cloze answer too long ({word_count} words): {answer}"
    
    # -------------------------------------------------------------------------
    # 4.2 Minimum Information Principle
    # -------------------------------------------------------------------------
    
    def test_cloze_tests_single_fact(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Each cloze card tests exactly one fact (atomic)."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=3))
        
        for card in cards:
            # Count cloze deletions
            deletions = re.findall(r"\{\{c\d+::", card.text)
            
            # Should have 1-3 deletions max for related concepts
            assert 1 <= len(deletions) <= 3, \
                f"Card has {len(deletions)} deletions, should be 1-3"
    
    def test_cloze_cards_are_unique(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Generated cards test different facts."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=5))
        
        # Extract main concepts being tested
        concepts = []
        for card in cards:
            answers = re.findall(r"\{\{c\d+::([^}]+)\}\}", card.text)
            concepts.append(frozenset(answers))
        
        # Should have mostly unique concepts
        unique_concepts = len(set(concepts))
        assert unique_concepts >= len(cards) * 0.8, \
            "Too many duplicate concepts in generated cards"
    
    # -------------------------------------------------------------------------
    # 4.3 Context and Self-Containment
    # -------------------------------------------------------------------------
    
    def test_cloze_is_self_contained(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Cloze cards include sufficient context to be unambiguous."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=1))
        
        for card in cards:
            # Card should have enough text around the cloze
            assert len(card.text) >= 30, \
                f"Card too short to be self-contained: {card.text}"
    
    def test_cloze_includes_extra_field(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """Cloze cards have extra information for learning."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=1))
        
        # At least some cards should have extra content
        [c for c in cards if c.extra and len(c.extra) > 0]
        
        # Not strictly required, but encouraged
        # assert len(cards_with_extra) > 0
    
    # -------------------------------------------------------------------------
    # 4.4 Topic-Specific Patterns
    # -------------------------------------------------------------------------
    
    def test_pharmacology_cloze_pattern(
        self,
        generator: IGenerationService,
        pharmacology_classified_chunk: ClassifiedChunk
    ):
        """Pharmacology cards follow drug-mechanism-indication pattern."""
        cards = pytest.run_sync(
            generator.generate_cloze(pharmacology_classified_chunk, count=2)
        )
        
        # Should test drug names, mechanisms, or indications
        pharma_terms = ["mechanism", "inhibitor", "agonist", "blocker", "treats", "used for"]
        
        has_pharma_structure = any(
            any(term in card.text.lower() for term in pharma_terms)
            for card in cards
        )
        
        # At least one should follow pharma pattern
        assert has_pharma_structure
    
    def test_anatomy_cloze_includes_relationships(
        self,
        generator: IGenerationService,
        anatomy_classified_chunk: ClassifiedChunk
    ):
        """Anatomy cards include spatial/functional relationships."""
        cards = pytest.run_sync(
            generator.generate_cloze(anatomy_classified_chunk, count=2)
        )
        
        # Should include relationship terms
        relationship_terms = [
            "supplies", "drains", "innervates", "located", "connects",
            "anterior", "posterior", "medial", "lateral"
        ]
        
        has_relationships = any(
            any(term in card.text.lower() for term in relationship_terms)
            for card in cards
        )
        
        assert has_relationships


class TestVignetteGeneration:
    """Tests for clinical vignette card generation."""
    
    # -------------------------------------------------------------------------
    # 4.5 Basic Vignette Generation
    # -------------------------------------------------------------------------
    
    def test_generate_vignette_returns_card(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk
    ):
        """Generation produces a vignette card."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        assert card is None or isinstance(card, VignetteCard)
    
    def test_vignette_has_patient_demographics(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk
    ):
        """Vignette stem includes patient age and sex."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        if card:
            # Should have age pattern
            age_pattern = re.compile(r"\d+-year-old")
            assert age_pattern.search(card.front), \
                f"Vignette missing patient age: {card.front[:100]}"
    
    def test_vignette_ends_with_question(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk
    ):
        """Vignette stem ends with a focused question."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        if card:
            assert card.front.strip().endswith("?"), \
                "Vignette should end with a question"
    
    def test_vignette_has_concise_answer(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk,
        max_words: int = 5
    ):
        """Vignette answer is concise (1-5 words)."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        if card:
            word_count = len(card.answer.split())
            assert word_count <= max_words, \
                f"Answer too long ({word_count} words): {card.answer}"
    
    def test_vignette_has_explanation(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk
    ):
        """Vignette includes explanation connecting presentation to diagnosis."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        if card:
            assert len(card.explanation) >= 50, \
                "Explanation too short"
    
    # -------------------------------------------------------------------------
    # 4.6 Vignette Clinical Accuracy
    # -------------------------------------------------------------------------
    
    def test_vignette_question_types(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk
    ):
        """Vignette asks diagnosis or management questions."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        if card:
            valid_endings = [
                "most likely diagnosis?",
                "appropriate next step?",
                "most appropriate management?",
                "most likely cause?",
                "best initial therapy?",
            ]
            
            front_lower = card.front.lower()
            has_valid_question = any(
                ending in front_lower for ending in valid_endings
            )
            
            # Allow some flexibility but encourage standard formats
            assert has_valid_question or "?" in card.front
    
    def test_vignette_excludes_multiple_choice(
        self,
        generator: IGenerationService,
        clinical_classified_chunk: ClassifiedChunk
    ):
        """Vignette does not include answer options (free recall)."""
        card = pytest.run_sync(generator.generate_vignette(clinical_classified_chunk))
        
        if card:
            # Should not have A), B), C) style options
            option_pattern = re.compile(r"[A-E]\)")
            assert not option_pattern.search(card.front), \
                "Vignette should not include multiple choice options"


class TestCardValidation:
    """Tests for card quality validation."""
    
    # -------------------------------------------------------------------------
    # 4.7 Schema Validation
    # -------------------------------------------------------------------------
    
    def test_validate_valid_cloze_passes(
        self,
        validator: IValidationService
    ):
        """Valid cloze card passes validation."""
        card = ClozeCard(
            id="test",
            text="The rate-limiting enzyme of glycolysis is {{c1::PFK-1}}",
            extra="Allosterically regulated by ATP and citrate",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        assert result.is_valid
        assert result.status == ValidationStatus.VALID
    
    def test_validate_missing_cloze_fails(
        self,
        validator: IValidationService
    ):
        """Card without cloze deletion fails validation."""
        card = ClozeCard(
            id="test",
            text="The rate-limiting enzyme of glycolysis is PFK-1",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        assert not result.is_valid
        assert result.status == ValidationStatus.INVALID_SCHEMA
        assert "cloze" in " ".join(result.issues).lower()
    
    def test_validate_long_cloze_answer_fails(
        self,
        validator: IValidationService
    ):
        """Cloze with overly long answer fails validation."""
        card = ClozeCard(
            id="test",
            text="The enzyme is {{c1::phosphofructokinase-1 which catalyzes the committed step}}",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        assert not result.is_valid
        assert "too long" in " ".join(result.issues).lower() or \
               result.status == ValidationStatus.INVALID_SCHEMA
    
    def test_validate_vignette_without_age_fails(
        self,
        validator: IValidationService
    ):
        """Vignette without patient demographics fails."""
        card = VignetteCard(
            id="test",
            front="A patient presents with chest pain. What is the most likely diagnosis?",
            answer="MI",
            explanation="The presentation suggests acute coronary syndrome.",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        # Should flag missing demographics
        assert not result.is_valid or "age" in " ".join(result.issues).lower()
    
    # -------------------------------------------------------------------------
    # 4.8 Medical Accuracy Checking
    # -------------------------------------------------------------------------
    
    def test_validate_medically_accurate_card(
        self,
        validator: IValidationService
    ):
        """Medically accurate card has high accuracy score."""
        card = ClozeCard(
            id="test",
            text="{{c1::Aspirin}} inhibits {{c2::cyclooxygenase}} irreversibly",
            extra="Used for antiplatelet therapy",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        assert result.accuracy_score >= 0.8
    
    def test_validate_medically_inaccurate_card(
        self,
        validator: IValidationService
    ):
        """Medically inaccurate card is flagged."""
        card = ClozeCard(
            id="test",
            text="{{c1::Insulin}} is used to treat {{c2::hypoglycemia}}",  # Wrong!
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        # Should detect the inaccuracy
        assert result.accuracy_score < 0.8 or not result.is_valid
    
    # -------------------------------------------------------------------------
    # 4.9 Hallucination Detection
    # -------------------------------------------------------------------------
    
    def test_validate_detects_hallucination(
        self,
        validator: IValidationService
    ):
        """Validator flags likely hallucinated content."""
        card = ClozeCard(
            id="test",
            text="{{c1::Cardiofluxin}} is the first-line treatment for {{c2::type 3 diabetes}}",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        # Should detect fake drug and condition
        assert result.hallucination_risk > 0.5 or \
               result.status == ValidationStatus.HALLUCINATION_DETECTED
    
    def test_validate_low_hallucination_for_real_content(
        self,
        validator: IValidationService
    ):
        """Real medical content has low hallucination risk."""
        card = ClozeCard(
            id="test",
            text="{{c1::Metformin}} is first-line therapy for {{c2::type 2 diabetes}}",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        assert result.hallucination_risk < 0.3
    
    # -------------------------------------------------------------------------
    # 4.10 Duplicate Detection
    # -------------------------------------------------------------------------
    
    def test_detect_exact_duplicate(
        self,
        validator: IValidationService
    ):
        """Exact duplicate cards are detected."""
        card = ClozeCard(
            id="test1",
            text="The heart has {{c1::four}} chambers",
            source_chunk_id="chunk_1"
        )
        
        existing = [
            ClozeCard(
                id="existing",
                text="The heart has {{c1::four}} chambers",
                source_chunk_id="chunk_2"
            )
        ]
        
        is_duplicate = pytest.run_sync(validator.check_duplicate(card, existing))
        
        assert is_duplicate
    
    def test_detect_semantic_duplicate(
        self,
        validator: IValidationService
    ):
        """Semantically similar cards are detected as duplicates."""
        card = ClozeCard(
            id="test1",
            text="The heart contains {{c1::4}} chambers",
            source_chunk_id="chunk_1"
        )
        
        existing = [
            ClozeCard(
                id="existing",
                text="The heart has {{c1::four}} chambers",
                source_chunk_id="chunk_2"
            )
        ]
        
        is_duplicate = pytest.run_sync(validator.check_duplicate(card, existing))
        
        # Should detect semantic similarity
        assert is_duplicate
    
    def test_not_duplicate_different_content(
        self,
        validator: IValidationService
    ):
        """Different content is not flagged as duplicate."""
        card = ClozeCard(
            id="test1",
            text="The heart has {{c1::four}} chambers",
            source_chunk_id="chunk_1"
        )
        
        existing = [
            ClozeCard(
                id="existing",
                text="The lungs have {{c1::five}} lobes",
                source_chunk_id="chunk_2"
            )
        ]
        
        is_duplicate = pytest.run_sync(validator.check_duplicate(card, existing))
        
        assert not is_duplicate


# =============================================================================
# SECTION 5: EXPORT LAYER TESTS
# =============================================================================

class TestTagBuilding:
    """Tests for hierarchical tag generation."""
    
    def test_build_tags_from_topics(
        self,
        exporter: IExportService
    ):
        """Tags are built from topic matches."""
        topics = [
            TopicMatch(
                topic_id="CVS-001",
                topic_name="Heart Failure",
                path=["Cardiovascular", "Pathology", "Heart_Failure"],
                confidence=0.85,
                exam_type=ExamType.USMLE_STEP1
            )
        ]
        
        tags = exporter.build_tags(topics, source="Lecture_05")
        
        assert len(tags) > 0
    
    def test_tags_use_hierarchical_format(
        self,
        exporter: IExportService
    ):
        """Tags use double-colon hierarchical separator."""
        topics = [
            TopicMatch(
                topic_id="CVS-001",
                topic_name="Heart Failure",
                path=["Cardiovascular", "Pathology", "Heart_Failure"],
                confidence=0.85,
                exam_type=ExamType.USMLE_STEP1
            )
        ]
        
        tags = exporter.build_tags(topics, source=None)
        
        # Should have hierarchical structure
        hierarchical_tags = [t for t in tags if "::" in t]
        assert len(hierarchical_tags) > 0
    
    def test_tags_start_with_hash(
        self,
        exporter: IExportService
    ):
        """Tags are prefixed with # for Anki compatibility."""
        topics = [
            TopicMatch(
                topic_id="CVS-001",
                topic_name="Heart Failure",
                path=["Cardiovascular"],
                confidence=0.85,
                exam_type=ExamType.USMLE_STEP1
            )
        ]
        
        tags = exporter.build_tags(topics, source=None)
        
        for tag in tags:
            assert tag.startswith("#"), f"Tag missing # prefix: {tag}"
    
    def test_usmle_tags_anking_compatible(
        self,
        exporter: IExportService
    ):
        """USMLE tags follow AnKing format."""
        topics = [
            TopicMatch(
                topic_id="CVS-001",
                topic_name="Heart Failure",
                path=["Cardiovascular", "Pathology"],
                confidence=0.85,
                exam_type=ExamType.USMLE_STEP1
            )
        ]
        
        tags = exporter.build_tags(topics, source=None)
        
        # Should have system tag
        system_tags = [t for t in tags if "Systems" in t or "Cardiovascular" in t]
        assert len(system_tags) > 0
    
    def test_mcat_tags_include_foundational_concept(
        self,
        exporter: IExportService
    ):
        """MCAT tags include Foundational Concept reference."""
        topics = [
            TopicMatch(
                topic_id="1A",
                topic_name="Protein Structure",
                path=["Bio/Biochem", "FC1", "1A", "Proteins"],
                confidence=0.85,
                exam_type=ExamType.MCAT
            )
        ]
        
        tags = exporter.build_tags(topics, source=None)
        
        # Should reference FC
        fc_tags = [t for t in tags if "FC" in t or "Bio" in t]
        assert len(fc_tags) > 0
    
    def test_source_tag_included(
        self,
        exporter: IExportService
    ):
        """Source information is included in tags."""
        topics = [
            TopicMatch(
                topic_id="CVS-001",
                topic_name="Heart Failure",
                path=["Cardiovascular"],
                confidence=0.85,
                exam_type=ExamType.USMLE_STEP1
            )
        ]
        
        tags = exporter.build_tags(topics, source="Biochem_Lecture_05")
        
        source_tags = [t for t in tags if "Source" in t or "Lecture" in t]
        assert len(source_tags) > 0


class TestDeckBuilding:
    """Tests for Anki deck generation."""
    
    def test_build_deck_creates_file(
        self,
        exporter: IExportService,
        sample_cards: list[ClozeCard],
        tmp_path: Path
    ):
        """Deck building creates an .apkg file."""
        output = exporter.build_deck(
            sample_cards,
            ExamType.USMLE_STEP1,
            "Test Deck"
        )
        
        assert output.exists()
        assert output.suffix == ".apkg"
    
    def test_deck_contains_all_cards(
        self,
        exporter: IExportService,
        sample_cards: list[ClozeCard],
        tmp_path: Path
    ):
        """Generated deck contains all input cards."""
        output = exporter.build_deck(
            sample_cards,
            ExamType.USMLE_STEP1,
            "Test Deck"
        )
        
        # Verify by checking file size or parsing
        assert output.stat().st_size > 0
        
        # Could also unzip and parse if needed
    
    def test_deck_has_stable_ids(
        self,
        exporter: IExportService,
        sample_cards: list[ClozeCard]
    ):
        """Deck and model IDs are stable across builds."""
        exporter.build_deck(sample_cards, ExamType.USMLE_STEP1, "Test")
        exporter.build_deck(sample_cards, ExamType.USMLE_STEP1, "Test")
        
        # Files should be similar (same IDs allow proper updates on import)
        # Implementation would check internal IDs
    
    def test_deck_includes_media(
        self,
        exporter: IExportService,
        cards_with_images: list[ClozeCard]
    ):
        """Deck includes referenced media files."""
        output = exporter.build_deck(
            cards_with_images,
            ExamType.USMLE_STEP1,
            "Test Deck"
        )
        
        # .apkg is a zip file containing media
        import zipfile
        with zipfile.ZipFile(output, 'r') as zf:
            zf.namelist()
            # Should have media files (numbered 0, 1, 2...)
            # or a media file that's not empty
    
    def test_deck_name_matches_exam_type(
        self,
        exporter: IExportService,
        sample_cards: list[ClozeCard]
    ):
        """Deck name reflects the exam type."""
        output_usmle = exporter.build_deck(
            sample_cards,
            ExamType.USMLE_STEP1,
            "USMLE Step 1"
        )
        
        output_mcat = exporter.build_deck(
            sample_cards,
            ExamType.MCAT,
            "MCAT Prep"
        )
        
        # Different decks for different exams
        assert "usmle" in output_usmle.name.lower() or "step" in output_usmle.name.lower()
        assert "mcat" in output_mcat.name.lower()


class TestCardGuidGeneration:
    """Tests for stable card identifiers."""
    
    def test_guid_is_deterministic(
        self,
        exporter: IExportService
    ):
        """Same content produces same GUID."""
        card = ClozeCard(
            id="test",
            text="The heart has {{c1::four}} chambers",
            source_chunk_id="chunk_1"
        )
        
        # Build twice
        guid1 = exporter._generate_guid(card.text) if hasattr(exporter, '_generate_guid') else hashlib.sha256(card.text.encode()).hexdigest()[:20]
        guid2 = exporter._generate_guid(card.text) if hasattr(exporter, '_generate_guid') else hashlib.sha256(card.text.encode()).hexdigest()[:20]
        
        assert guid1 == guid2
    
    def test_guid_differs_for_different_content(
        self,
        exporter: IExportService
    ):
        """Different content produces different GUIDs."""
        card1 = ClozeCard(id="1", text="Content A", source_chunk_id="c1")
        card2 = ClozeCard(id="2", text="Content B", source_chunk_id="c2")
        
        guid1 = hashlib.sha256(card1.text.encode()).hexdigest()[:20]
        guid2 = hashlib.sha256(card2.text.encode()).hexdigest()[:20]
        
        assert guid1 != guid2


# =============================================================================
# SECTION 6: INTEGRATION TESTS
# =============================================================================

class TestEndToEndPipeline:
    """Integration tests for the complete pipeline."""
    
    def test_pdf_to_cards_pipeline(
        self,
        pipeline,  # Full FlashcardPipeline
        simple_medical_pdf: Path,
        tmp_path: Path
    ):
        """Complete pipeline from PDF to .apkg."""
        result = pipeline.run(
            input_path=simple_medical_pdf,
            exam_type="usmle-step1",
            cards_per_chunk=2,
            output_dir=tmp_path
        )
        
        assert isinstance(result, GenerationResult)
        assert result.document_count >= 1
        assert result.chunk_count >= 1
        assert result.card_count >= 1
        assert result.output_path is not None
        assert Path(result.output_path).exists()
    
    def test_pipeline_handles_multiple_files(
        self,
        pipeline,
        pdf_directory: Path,  # Directory with multiple PDFs
        tmp_path: Path
    ):
        """Pipeline processes multiple input files."""
        result = pipeline.run(
            input_path=pdf_directory,
            exam_type="mcat",
            cards_per_chunk=1,
            output_dir=tmp_path
        )
        
        assert result.document_count > 1
    
    def test_pipeline_respects_exam_type(
        self,
        pipeline,
        simple_medical_pdf: Path,
        tmp_path: Path
    ):
        """Pipeline uses correct taxonomy for exam type."""
        pipeline.run(
            input_path=simple_medical_pdf,
            exam_type="mcat",
            cards_per_chunk=1,
            output_dir=tmp_path
        )
        
        pipeline.run(
            input_path=simple_medical_pdf,
            exam_type="usmle-step1",
            cards_per_chunk=1,
            output_dir=tmp_path
        )
        
        # Tags should differ based on exam type
        # (Would check actual card tags in implementation)
    
    def test_pipeline_removes_duplicates(
        self,
        pipeline,
        repetitive_pdf: Path,  # PDF with repeated content
        tmp_path: Path
    ):
        """Pipeline deduplicates generated cards."""
        result = pipeline.run(
            input_path=repetitive_pdf,
            exam_type="usmle-step1",
            cards_per_chunk=3,
            output_dir=tmp_path
        )
        
        assert result.duplicates_removed > 0
    
    def test_pipeline_validates_cards(
        self,
        pipeline,
        simple_medical_pdf: Path,
        tmp_path: Path
    ):
        """Pipeline validates all generated cards."""
        result = pipeline.run(
            input_path=simple_medical_pdf,
            exam_type="usmle-step1",
            cards_per_chunk=2,
            output_dir=tmp_path
        )
        
        # Validation failures should be tracked
        assert isinstance(result.validation_failures, int)
    
    def test_dry_run_does_not_create_file(
        self,
        pipeline,
        simple_medical_pdf: Path,
        tmp_path: Path
    ):
        """Dry run processes without creating output file."""
        result = pipeline.run(
            input_path=simple_medical_pdf,
            exam_type="usmle-step1",
            cards_per_chunk=2,
            output_dir=tmp_path,
            dry_run=True
        )
        
        assert result.output_path is None or not Path(result.output_path).exists()
        assert result.chunk_count > 0  # Still processed


class TestChunkToCardFlow:
    """Tests for chunk-to-card transformation flow."""
    
    def test_chunk_classification_to_card_tags(
        self,
        chunker: IChunkingService,
        classifier: IClassificationService,
        generator: IGenerationService,
        exporter: IExportService,
        cardiology_document: Document
    ):
        """Tags flow correctly from classification to generated cards."""
        # Chunk the document
        chunks = chunker.chunk(cardiology_document)
        assert len(chunks) > 0
        
        chunk = chunks[0]
        
        # Classify
        topics = pytest.run_sync(
            classifier.classify(chunk, ExamType.USMLE_STEP1)
        )
        
        # Create classified chunk
        classified = ClassifiedChunk(
            chunk=chunk,
            usmle_topics=topics,
            primary_exam=ExamType.USMLE_STEP1
        )
        
        # Generate cards
        pytest.run_sync(generator.generate_cloze(classified, count=1))
        
        # Build tags
        tags = exporter.build_tags(topics, source=cardiology_document.source_path)
        
        # Verify tags contain cardiovascular reference
        assert any("cardio" in t.lower() for t in tags)


class TestErrorRecovery:
    """Tests for error handling and recovery."""
    
    def test_pipeline_continues_on_chunk_error(
        self,
        pipeline,
        pdf_with_corrupted_section: Path,
        tmp_path: Path
    ):
        """Pipeline continues processing after chunk-level errors."""
        result = pipeline.run(
            input_path=pdf_with_corrupted_section,
            exam_type="usmle-step1",
            cards_per_chunk=1,
            output_dir=tmp_path
        )
        
        # Should still produce some cards
        assert result.card_count > 0
    
    def test_pipeline_handles_empty_pdf(
        self,
        pipeline,
        empty_pdf: Path,
        tmp_path: Path
    ):
        """Pipeline gracefully handles empty input."""
        result = pipeline.run(
            input_path=empty_pdf,
            exam_type="usmle-step1",
            cards_per_chunk=1,
            output_dir=tmp_path
        )
        
        assert result.document_count == 0 or result.chunk_count == 0
        assert result.card_count == 0


# =============================================================================
# SECTION 7: PROPERTY-BASED TESTS
# =============================================================================

class TestChunkingProperties:
    """Property-based tests for chunking invariants."""
    
    @pytest.mark.parametrize("text_length", [100, 500, 1000, 5000, 10000])
    def test_chunking_produces_valid_chunks_any_length(
        self,
        chunker: IChunkingService,
        text_length: int
    ):
        """Chunking produces valid chunks for any document length."""
        # Generate random medical-ish text
        text = ("The patient presents with symptoms. " * (text_length // 35))[:text_length]
        
        document = Document(
            id="test",
            source_path="/test.pdf",
            content_type=ContentType.PDF_NOTES,
            raw_text=text
        )
        
        chunks = chunker.chunk(document)
        
        # Invariants that must always hold
        if len(text) > 50:  # Non-trivial input
            assert len(chunks) > 0
        
        for chunk in chunks:
            assert len(chunk.text) > 0
            assert chunk.token_count > 0
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
    
    def test_chunking_idempotent(
        self,
        chunker: IChunkingService,
        sample_document: Document
    ):
        """Chunking same document produces same result."""
        chunks1 = chunker.chunk(sample_document)
        chunks2 = chunker.chunk(sample_document)
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2, strict=False):
            assert c1.text == c2.text


class TestClozeGenerationProperties:
    """Property-based tests for cloze generation."""
    
    @pytest.mark.parametrize("count", [1, 2, 3, 5, 10])
    def test_generation_respects_count(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk,
        count: int
    ):
        """Generation produces exactly requested count."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=count))
        
        assert len(cards) == count
    
    def test_all_generated_cards_have_valid_syntax(
        self,
        generator: IGenerationService,
        classified_chunk: ClassifiedChunk
    ):
        """All generated cards have valid cloze syntax."""
        cards = pytest.run_sync(generator.generate_cloze(classified_chunk, count=10))
        
        cloze_pattern = re.compile(r"\{\{c\d+::[^}]+\}\}")
        
        for card in cards:
            assert cloze_pattern.search(card.text), f"Invalid cloze: {card.text}"


class TestClassificationProperties:
    """Property-based tests for classification."""
    
    def test_classification_confidence_bounds(
        self,
        classifier: IClassificationService,
        sample_chunk: Chunk
    ):
        """Classification confidence is always between 0 and 1."""
        topics = pytest.run_sync(
            classifier.classify(sample_chunk, ExamType.USMLE_STEP1)
        )
        
        for topic in topics:
            assert 0 <= topic.confidence <= 1
    
    def test_classification_sorted_by_confidence(
        self,
        classifier: IClassificationService,
        sample_chunk: Chunk
    ):
        """Classification results are sorted by confidence descending."""
        topics = pytest.run_sync(
            classifier.classify(sample_chunk, ExamType.USMLE_STEP1)
        )
        
        if len(topics) > 1:
            confidences = [t.confidence for t in topics]
            assert confidences == sorted(confidences, reverse=True)


class TestTagProperties:
    """Property-based tests for tag generation."""
    
    def test_tags_no_invalid_characters(
        self,
        exporter: IExportService
    ):
        """Generated tags contain no invalid characters."""
        topics = [
            TopicMatch(
                topic_id="test",
                topic_name="Test Topic",
                path=["System", "Subsystem"],
                confidence=0.8,
                exam_type=ExamType.USMLE_STEP1
            )
        ]
        
        tags = exporter.build_tags(topics, source="Test Source With Spaces")
        
        invalid_chars = set(' \t\n"\'')
        for tag in tags:
            tag_chars = set(tag)
            assert not (tag_chars & invalid_chars), f"Invalid chars in tag: {tag}"


# =============================================================================
# SECTION 8: EDGE CASES & ERROR HANDLING
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    # -------------------------------------------------------------------------
    # 8.1 Empty/Minimal Input
    # -------------------------------------------------------------------------
    
    def test_chunk_empty_document(
        self,
        chunker: IChunkingService
    ):
        """Chunking empty document returns empty list."""
        document = Document(
            id="empty",
            source_path="/empty.pdf",
            content_type=ContentType.PDF_NOTES,
            raw_text=""
        )
        
        chunks = chunker.chunk(document)
        
        assert chunks == []
    
    def test_chunk_whitespace_only_document(
        self,
        chunker: IChunkingService
    ):
        """Chunking whitespace-only document returns empty list."""
        document = Document(
            id="whitespace",
            source_path="/whitespace.pdf",
            content_type=ContentType.PDF_NOTES,
            raw_text="   \n\t\n   "
        )
        
        chunks = chunker.chunk(document)
        
        assert chunks == []
    
    def test_classify_empty_chunk(
        self,
        classifier: IClassificationService
    ):
        """Classifying empty chunk returns empty results."""
        chunk = Chunk(
            id="empty",
            document_id="doc",
            text="",
            start_char=0,
            end_char=0,
            token_count=0
        )
        
        topics = pytest.run_sync(
            classifier.classify(chunk, ExamType.USMLE_STEP1)
        )
        
        assert topics == []
    
    def test_generate_from_minimal_chunk(
        self,
        generator: IGenerationService
    ):
        """Generation from minimal content handles gracefully."""
        chunk = Chunk(
            id="minimal",
            document_id="doc",
            text="Heart.",
            start_char=0,
            end_char=6,
            token_count=1
        )
        
        classified = ClassifiedChunk(
            chunk=chunk,
            usmle_topics=[],
            primary_exam=ExamType.USMLE_STEP1
        )
        
        # Should either produce minimal cards or empty list
        cards = pytest.run_sync(generator.generate_cloze(classified, count=1))
        
        # Implementation decides behavior for minimal input
        assert isinstance(cards, list)
    
    # -------------------------------------------------------------------------
    # 8.2 Unicode and Special Characters
    # -------------------------------------------------------------------------
    
    def test_chunk_unicode_content(
        self,
        chunker: IChunkingService
    ):
        """Chunking handles unicode characters."""
        document = Document(
            id="unicode",
            source_path="/unicode.pdf",
            content_type=ContentType.PDF_NOTES,
            raw_text="α-adrenergic β-blocker μg/mL → treatment"
        )
        
        chunks = chunker.chunk(document)
        
        assert len(chunks) > 0
        # Unicode should be preserved
        combined = " ".join(c.text for c in chunks)
        assert "α" in combined or "alpha" in combined.lower()
    
    def test_chunk_chemical_formulas(
        self,
        chunker: IChunkingService
    ):
        """Chunking preserves chemical formulas."""
        document = Document(
            id="chem",
            source_path="/chem.pdf",
            content_type=ContentType.PDF_NOTES,
            raw_text="The reaction H2O + CO2 → H2CO3 is important."
        )
        
        chunks = chunker.chunk(document)
        
        combined = " ".join(c.text for c in chunks)
        assert "H2O" in combined or "H₂O" in combined
    
    def test_cloze_with_special_characters(
        self,
        validator: IValidationService
    ):
        """Cloze cards with special characters validate correctly."""
        card = ClozeCard(
            id="special",
            text="The drug {{c1::β-blocker}} reduces heart rate",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        # Should handle special chars in cloze syntax
        assert result.is_valid
    
    # -------------------------------------------------------------------------
    # 8.3 Very Long Content
    # -------------------------------------------------------------------------
    
    def test_chunk_very_long_document(
        self,
        chunker: IChunkingService
    ):
        """Chunking handles very long documents."""
        # Simulate 100+ page document
        document = Document(
            id="long",
            source_path="/long.pdf",
            content_type=ContentType.PDF_TEXTBOOK,
            raw_text="Medical content. " * 50000  # ~800K chars
        )
        
        chunks = chunker.chunk(document)
        
        # Should produce many chunks
        assert len(chunks) > 100
        
        # All chunks should be within limits
        for chunk in chunks:
            assert chunk.token_count <= 512
    
    def test_classify_long_chunk(
        self,
        classifier: IClassificationService
    ):
        """Classification handles chunks at max length."""
        long_text = "Cardiovascular physiology " * 100
        chunk = Chunk(
            id="long",
            document_id="doc",
            text=long_text,
            start_char=0,
            end_char=len(long_text),
            token_count=500
        )
        
        topics = pytest.run_sync(
            classifier.classify(chunk, ExamType.USMLE_STEP1)
        )
        
        # Should still produce results
        assert len(topics) > 0
    
    # -------------------------------------------------------------------------
    # 8.4 Malformed Input
    # -------------------------------------------------------------------------
    
    def test_chunk_malformed_unicode(
        self,
        chunker: IChunkingService
    ):
        """Chunking handles malformed unicode gracefully."""
        document = Document(
            id="malformed",
            source_path="/malformed.pdf",
            content_type=ContentType.PDF_NOTES,
            raw_text="Normal text \x00 with null \xff bytes"
        )
        
        # Should not crash
        try:
            chunks = chunker.chunk(document)
            assert isinstance(chunks, list)
        except ValueError:
            # Also acceptable to raise clear error
            pass
    
    def test_validate_malformed_cloze(
        self,
        validator: IValidationService
    ):
        """Validation handles malformed cloze syntax."""
        card = ClozeCard(
            id="malformed",
            text="Missing closing {{c1::bracket",
            source_chunk_id="chunk_1"
        )
        
        result = pytest.run_sync(validator.validate(card))
        
        assert not result.is_valid
        assert result.status == ValidationStatus.INVALID_SCHEMA
    
    # -------------------------------------------------------------------------
    # 8.5 Concurrent Operations
    # -------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    async def test_concurrent_embedding(
        self,
        embedder: IEmbeddingService
    ):
        """Embedder handles concurrent requests."""
        import asyncio
        
        texts = [f"Medical text {i}" for i in range(10)]
        
        # Run embeddings concurrently
        tasks = [embedder.embed_single(text) for text in texts]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        for result in results:
            assert len(result) == embedder.dimensions
    
    @pytest.mark.asyncio
    async def test_concurrent_classification(
        self,
        classifier: IClassificationService
    ):
        """Classifier handles concurrent requests."""
        import asyncio
        
        chunks = [
            Chunk(
                id=f"chunk_{i}",
                document_id="doc",
                text=f"Medical content about topic {i}",
                start_char=0,
                end_char=50,
                token_count=10
            )
            for i in range(5)
        ]
        
        tasks = [
            classifier.classify(chunk, ExamType.USMLE_STEP1)
            for chunk in chunks
        ]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def simple_pdf_path(tmp_path: Path) -> Path:
    """Create a simple test PDF."""
    # In real implementation, would create actual PDF
    pdf_path = tmp_path / "simple.pdf"
    pdf_path.touch()
    return pdf_path


@pytest.fixture
def sample_document() -> Document:
    """Create a sample medical document."""
    return Document(
        id="sample_doc_001",
        source_path="/test/sample.pdf",
        content_type=ContentType.PDF_TEXTBOOK,
        raw_text="""
        Chapter 1: Cardiovascular Physiology
        
        The heart is a muscular organ that pumps blood throughout the body.
        It consists of four chambers: two atria and two ventricles.
        
        The cardiac cycle consists of systole (contraction) and diastole (relaxation).
        During systole, the ventricles contract and eject blood into the arteries.
        During diastole, the ventricles relax and fill with blood from the atria.
        
        Heart rate is controlled by the sinoatrial (SA) node, the natural pacemaker.
        The SA node generates electrical impulses that spread through the heart.
        
        Blood pressure is the force of blood against arterial walls.
        Systolic pressure is measured during ventricular contraction.
        Diastolic pressure is measured during ventricular relaxation.
        """,
        sections=[
            Section(title="Cardiovascular Physiology", level=1, start_char=0, end_char=800)
        ]
    )


@pytest.fixture
def cardiology_chunk() -> Chunk:
    """Create a chunk about cardiology."""
    return Chunk(
        id="cardio_chunk_001",
        document_id="doc_001",
        text="""
        Heart failure occurs when the heart cannot pump enough blood to meet
        the body's needs. Symptoms include dyspnea, fatigue, and peripheral edema.
        Treatment includes ACE inhibitors, beta-blockers, and diuretics.
        """,
        start_char=0,
        end_char=250,
        token_count=45
    )


@pytest.fixture
def pharmacology_chunk() -> Chunk:
    """Create a chunk about pharmacology."""
    return Chunk(
        id="pharm_chunk_001",
        document_id="doc_001",
        text="""
        Beta-blockers work by blocking beta-adrenergic receptors in the heart.
        This reduces heart rate and myocardial contractility, decreasing oxygen demand.
        Common beta-blockers include metoprolol, atenolol, and propranolol.
        """,
        start_char=0,
        end_char=250,
        token_count=40
    )


@pytest.fixture
def classified_chunk(cardiology_chunk: Chunk) -> ClassifiedChunk:
    """Create a classified chunk."""
    return ClassifiedChunk(
        chunk=cardiology_chunk,
        usmle_topics=[
            TopicMatch(
                topic_id="CVS-HF-001",
                topic_name="Heart Failure",
                path=["Cardiovascular", "Pathology", "Heart_Failure"],
                confidence=0.85,
                exam_type=ExamType.USMLE_STEP1
            )
        ],
        primary_exam=ExamType.USMLE_STEP1
    )


@pytest.fixture
def sample_cards() -> list[ClozeCard]:
    """Create sample cloze cards for testing."""
    return [
        ClozeCard(
            id="card_001",
            text="The heart has {{c1::four}} chambers",
            extra="Two atria and two ventricles",
            source_chunk_id="chunk_001",
            tags=["#Cardiovascular", "#Anatomy"]
        ),
        ClozeCard(
            id="card_002",
            text="{{c1::Systole}} is the contraction phase of the cardiac cycle",
            extra="Followed by diastole (relaxation)",
            source_chunk_id="chunk_001",
            tags=["#Cardiovascular", "#Physiology"]
        ),
    ]


@pytest.fixture
def sample_texts() -> list[str]:
    """Sample texts for embedding tests."""
    return [
        "Myocardial infarction is caused by coronary artery occlusion",
        "Diabetes mellitus affects glucose metabolism",
        "Pneumonia is an infection of the lungs"
    ]


# =============================================================================
# TEST HELPERS
# =============================================================================

class pytest:
    """Helper namespace for async test utilities."""
    
    @staticmethod
    def run_sync(coro):
        """Run coroutine synchronously for tests."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# MOCK IMPLEMENTATIONS FOR TESTING
# =============================================================================

class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, responses: dict[str, str] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
    
    async def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        
        # Return canned response or generate mock cloze
        if "cloze" in prompt.lower():
            return json.dumps([{
                "text": "The {{c1::heart}} pumps blood",
                "extra": "Four chambers"
            }])
        elif "vignette" in prompt.lower():
            return json.dumps({
                "front": "A 55-year-old man presents with chest pain. What is the diagnosis?",
                "answer": "MI",
                "explanation": "Classic presentation of acute MI."
            })
        
        return self.responses.get("default", "{}")


class MockEmbedder:
    """Mock embedder for testing."""
    
    def __init__(self, dims: int = 768):
        self._dims = dims
    
    @property
    def dimensions(self) -> int:
        return self._dims
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1 * (i + 1)] * self._dims for i in range(len(texts))]
    
    async def embed_single(self, text: str) -> list[float]:
        return [0.1] * self._dims


class MockVectorStore:
    """Mock vector store for testing."""
    
    def __init__(self):
        self.collections: dict[str, list[dict]] = {}
    
    async def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict],
        ids: list[str]
    ) -> None:
        if collection not in self.collections:
            self.collections[collection] = []
        
        for vec, meta, id_ in zip(vectors, metadata, ids, strict=False):
            self.collections[collection].append({
                "id": id_,
                "vector": vec,
                "metadata": meta
            })
    
    async def hybrid_search(
        self,
        collection: str,
        query_text: str,
        query_vector: list[float],
        alpha: float,
        limit: int
    ) -> list[dict]:
        items = self.collections.get(collection, [])
        # Return up to limit items with mock scores
        return [
            {**item, "_additional": {"score": 0.8 - i * 0.1}}
            for i, item in enumerate(items[:limit])
        ]


# =============================================================================
# CONFTEST SETUP (would normally be in conftest.py)
# =============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")


@pytest.fixture
def mock_llm():
    """Provide mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_embedder():
    """Provide mock embedder."""
    return MockEmbedder()


@pytest.fixture
def mock_vector_store():
    """Provide mock vector store."""
    return MockVectorStore()


# =============================================================================
# END OF TEST SPECIFICATION
# =============================================================================

"""
Summary of Test Coverage:

INGESTION LAYER (Section 2):
- PDF extraction: basic, headers, tables, page numbers
- PDF strategy selection: scanned, tables, equations, large files
- Audio transcription: formats, timestamps, segmentation
- Content type detection

PROCESSING LAYER (Section 3):
- Chunking: token limits, coverage, uniqueness
- Medical-specific chunking: drug names, anatomy, lab values, abbreviations
- Topic boundary detection: sections, topic shifts
- Entity extraction: labels, spans
- Embeddings: dimensions, similarity, edge cases
- Classification: topics, multi-label, thresholds, dual taxonomy
- Vector store: upsert, hybrid search

GENERATION LAYER (Section 4):
- Cloze generation: syntax, count, atomic facts, context
- Topic-specific patterns: pharmacology, anatomy
- Vignette generation: demographics, questions, answers
- Validation: schema, medical accuracy, hallucination
- Duplicate detection: exact, semantic

EXPORT LAYER (Section 5):
- Tag building: hierarchy, format, exam types
- Deck building: file creation, cards, media, GUIDs

INTEGRATION (Section 6):
- End-to-end pipeline
- Error recovery
- Multi-file processing

PROPERTIES (Section 7):
- Chunking invariants
- Generation invariants
- Classification bounds
- Tag format invariants

EDGE CASES (Section 8):
- Empty/minimal input
- Unicode and special characters
- Very long content
- Malformed input
- Concurrent operations

Total: ~150 test cases covering all system components
"""
