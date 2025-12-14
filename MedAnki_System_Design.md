# MedAnki: System Design Architecture
## A Unified MCAT/USMLE Flashcard Generation System

**Version:** 1.0  
**Author:** System Design Document  
**Date:** December 2025

---

## Executive Summary

MedAnki is a local CLI tool that transforms raw medical education materials (PDFs, lecture recordings, transcripts, handwritten notes) into high-quality Anki flashcards automatically tagged against AAMC (MCAT) and NBME (USMLE) content taxonomies. The system solves the critical "joining problem"—semantically matching arbitrary lecture content to standardized exam topics—through a RAG-based classification pipeline using medical-domain embeddings.

**Key Differentiators:**
- Dual taxonomy support (MCAT: 10 FCs × 23 categories; USMLE: 18 systems × 10 disciplines)
- Hybrid search (BM25 + semantic) for medical abbreviation handling
- Two card types: concept-based cloze deletions + clinical vignette Q&A
- AnKing-compatible hierarchical tagging for deck interoperability
- LLM-powered quality validation with hallucination detection

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MedAnki CLI Application                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Ingestion  │───▶│  Processing  │───▶│  Generation  │───▶│    Export    │  │
│  │    Layer     │    │    Layer     │    │    Layer     │    │    Layer     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │                   │          │
│         ▼                   ▼                   ▼                   ▼          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         Shared Services Layer                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │  Config     │  │  Taxonomy   │  │    LLM      │  │   Cache     │     │   │
│  │  │  Manager    │  │   Service   │  │   Client    │  │   Layer     │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│  ┌───────────────────────────────────┴───────────────────────────────────────┐ │
│  │                           Data Layer                                       │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐    │ │
│  │  │   Weaviate      │  │   SQLite        │  │   File System           │    │ │
│  │  │ (Vector Store)  │  │ (Metadata/Jobs) │  │ (Media, Exports)        │    │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | Key Components |
|-------|----------------|----------------|
| **Ingestion** | Accept and normalize diverse input formats | PDF extractor, Audio transcriber, Image OCR |
| **Processing** | Chunk, embed, classify against taxonomies | Chunker, Embedder, Classifier |
| **Generation** | Create flashcards from classified chunks | Card generator, Validator, Deduplicator |
| **Export** | Package cards for Anki consumption | genanki builder, AnkiConnect sync |
| **Shared Services** | Cross-cutting concerns | Config, Taxonomy, LLM abstraction, Caching |
| **Data** | Persistent storage | Vectors, metadata, job state, media files |

---

## 2. Component Deep Dives

### 2.1 Ingestion Layer

The ingestion layer normalizes heterogeneous inputs into a common `Document` representation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ingestion Layer                               │
│                                                                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│   │   PDF    │  │  Audio   │  │  Image   │  │  Text    │           │
│   │ Ingestor │  │ Ingestor │  │ Ingestor │  │ Ingestor │           │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│        │             │             │             │                   │
│        │    ┌────────┴────────┐    │             │                   │
│        │    │    Whisper      │    │             │                   │
│        │    │  (via API or    │    │             │                   │
│        │    │   local model)  │    │             │                   │
│        │    └────────┬────────┘    │             │                   │
│        │             │             │             │                   │
│        ▼             ▼             ▼             ▼                   │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                    Document Normalizer                        │  │
│   │  - Converts all inputs to unified Document schema             │  │
│   │  - Extracts metadata (source, timestamps, page numbers)       │  │
│   │  - Detects content type (lecture, textbook, notes)            │  │
│   └──────────────────────────────────────────────────────────────┘  │
│                                │                                     │
│                                ▼                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                     Document Store                            │  │
│   │  SQLite: documents(id, source_path, content_type, raw_text,  │  │
│   │          extracted_at, metadata_json)                         │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

#### PDF Extraction Strategy

```python
# Marker is the primary extractor; fall back based on document characteristics
class PDFExtractionStrategy:
    """Select optimal extraction method based on PDF characteristics."""
    
    def select_extractor(self, pdf_path: Path) -> Extractor:
        analysis = self._analyze_pdf(pdf_path)
        
        if analysis.is_scanned:
            return PaddleOCRExtractor()  # OCR-first pipeline
        elif analysis.has_complex_tables:
            return DoclingExtractor()    # Best table handling
        elif analysis.has_heavy_math:
            return NougatExtractor()     # Superior LaTeX
        else:
            return MarkerExtractor(use_llm=analysis.page_count < 50)
    
    def _analyze_pdf(self, path: Path) -> PDFAnalysis:
        # Quick heuristic analysis: text layer presence, table density, etc.
        ...
```

**Tool Selection Matrix:**

| Document Type | Primary Tool | Fallback | Notes |
|---------------|--------------|----------|-------|
| Textbooks (Kaplan, FA) | Marker + LLM | Docling | LLM mode for tables |
| Lecture slides | Marker | PyMuPDF4LLM | Force OCR for image-heavy |
| Scanned notes | PaddleOCR → Marker | Tesseract | PP-StructureV3 |
| Research papers | Marker | Nougat | Multi-column handling |
| High volume (>100 pages) | PyMuPDF4LLM | Marker | Speed priority |

#### Audio Transcription Pipeline

```python
class AudioIngestor:
    """Transcribe lecture recordings with speaker diarization."""
    
    def __init__(self, whisper_model: str = "large-v3"):
        self.transcriber = WhisperTranscriber(model=whisper_model)
        self.diarizer = PyAnnoteDiarizer()  # Optional speaker separation
    
    async def ingest(self, audio_path: Path) -> Document:
        # 1. Transcribe with word-level timestamps
        transcript = await self.transcriber.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"
        )
        
        # 2. Optional: diarize for multi-speaker lectures
        if self.config.enable_diarization:
            speakers = await self.diarizer.diarize(audio_path)
            transcript = self._merge_diarization(transcript, speakers)
        
        # 3. Segment by natural pauses and topic shifts
        segments = self._segment_transcript(transcript)
        
        return Document(
            content=transcript.text,
            segments=segments,
            metadata={"duration": transcript.duration, "source": str(audio_path)}
        )
```

### 2.2 Processing Layer

The processing layer transforms raw documents into classified, embeddable chunks.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Processing Layer                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Medical NLP Pipeline                             ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   ││
│  │  │   scispaCy   │  │   UMLS       │  │  Abbreviation│                   ││
│  │  │   (NER)      │──▶   Linker     │──▶   Expander   │                   ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Topic-Aware Chunker                                   ││
│  │                                                                          ││
│  │  Input Document ───▶ Section Detection ───▶ Semantic Boundaries ───▶    ││
│  │                      (headers, slides)      (topic shifts)               ││
│  │                                                                          ││
│  │  ───▶ Medical Term Preservation ───▶ Chunk Assembly ───▶ Chunks[]       ││
│  │       (drug names, anatomy)          (400-512 tokens)                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Embedding Service                                ││
│  │                                                                          ││
│  │  ┌─────────────────────────────────────────────────────────────────┐    ││
│  │  │  PubMedBERT (neuml/pubmedbert-base-embeddings)                  │    ││
│  │  │  - 768 dimensions                                                │    ││
│  │  │  - Batch size: 32 for GPU, 8 for CPU                            │    ││
│  │  │  - Max sequence: 512 tokens                                      │    ││
│  │  └─────────────────────────────────────────────────────────────────┘    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Taxonomy Classification Service                       ││
│  │                                                                          ││
│  │   Chunk Embedding ───▶ Hybrid Search ───▶ Multi-Label Assignment        ││
│  │                        (BM25 + Vector)    (dynamic threshold)            ││
│  │                              │                                           ││
│  │                              ▼                                           ││
│  │   ┌─────────────┐    ┌─────────────┐                                    ││
│  │   │ MCAT Topics │    │USMLE Topics │                                    ││
│  │   │ (pre-embed) │    │ (pre-embed) │                                    ││
│  │   └─────────────┘    └─────────────┘                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Chunking Algorithm

```python
from dataclasses import dataclass
from typing import List, Optional
import spacy

@dataclass
class Chunk:
    text: str
    start_char: int
    end_char: int
    page_number: Optional[int]
    section_header: Optional[str]
    entities: List[dict]  # UMLS-linked entities
    
class MedicalChunker:
    """Topic-boundary-aware chunking for medical content."""
    
    def __init__(
        self,
        target_tokens: int = 450,
        max_tokens: int = 512,
        overlap_tokens: int = 75,
        min_tokens: int = 100
    ):
        self.nlp = spacy.load("en_core_sci_lg")  # scispaCy
        self.nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True})
        self.tokenizer = AutoTokenizer.from_pretrained("neuml/pubmedbert-base-embeddings")
        
        self.target = target_tokens
        self.max = max_tokens
        self.overlap = overlap_tokens
        self.min = min_tokens
        
        # Medical terms that should never be split
        self.protected_patterns = [
            r"\b\d+\s*(mg|mcg|mL|mg/dL|mmol/L|mEq/L)\b",  # Lab values with units
            r"\b[A-Z]{2,5}\b",  # Abbreviations (CHF, DVT, etc.)
        ]
    
    def chunk(self, document: Document) -> List[Chunk]:
        # 1. Run NLP pipeline for entity recognition
        doc = self.nlp(document.content)
        
        # 2. Identify natural boundaries
        boundaries = self._find_boundaries(doc, document)
        
        # 3. Build chunks respecting boundaries and token limits
        chunks = []
        current_start = 0
        
        for boundary in boundaries:
            segment = document.content[current_start:boundary]
            segment_chunks = self._split_segment(segment, current_start, doc)
            chunks.extend(segment_chunks)
            current_start = boundary
        
        # 4. Add overlap for context continuity
        chunks = self._add_overlap(chunks, document.content)
        
        return chunks
    
    def _find_boundaries(self, doc, document: Document) -> List[int]:
        """Find natural topic boundaries."""
        boundaries = []
        
        # Section headers (if extracted from PDF structure)
        if document.sections:
            boundaries.extend(s.start_char for s in document.sections)
        
        # Paragraph breaks with topic shift detection
        for i, sent in enumerate(doc.sents):
            if i > 0:
                prev_ents = set(e.label_ for e in list(doc.sents)[i-1].ents)
                curr_ents = set(e.label_ for e in sent.ents)
                # Topic shift: different entity types appearing
                if len(prev_ents & curr_ents) == 0 and len(curr_ents) > 0:
                    boundaries.append(sent.start_char)
        
        return sorted(set(boundaries))
    
    def _split_segment(self, text: str, offset: int, doc) -> List[Chunk]:
        """Split a segment into appropriately-sized chunks."""
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= self.max:
            return [Chunk(
                text=text.strip(),
                start_char=offset,
                end_char=offset + len(text),
                page_number=None,
                section_header=None,
                entities=self._extract_entities(text, doc)
            )]
        
        # Need to split - find sentence boundaries
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sent in self.nlp(text).sents:
            sent_tokens = len(self.tokenizer.encode(sent.text))
            
            if current_tokens + sent_tokens > self.target:
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append(Chunk(
                        text=chunk_text,
                        start_char=offset,
                        end_char=offset + len(chunk_text),
                        page_number=None,
                        section_header=None,
                        entities=self._extract_entities(chunk_text, doc)
                    ))
                    offset += len(chunk_text) + 1
                current_chunk = [sent.text]
                current_tokens = sent_tokens
            else:
                current_chunk.append(sent.text)
                current_tokens += sent_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(Chunk(
                text=chunk_text,
                start_char=offset,
                end_char=offset + len(chunk_text),
                page_number=None,
                section_header=None,
                entities=self._extract_entities(chunk_text, doc)
            ))
        
        return chunks
```

#### Taxonomy Classification

```python
from typing import List, Dict, Tuple
import numpy as np
from enum import Enum

class ExamType(Enum):
    MCAT = "mcat"
    USMLE_STEP1 = "usmle_step1"
    USMLE_STEP2 = "usmle_step2"

@dataclass
class TopicMatch:
    topic_id: str
    topic_name: str
    path: List[str]  # Hierarchical path (e.g., ["Bio/Biochem", "FC1", "1A", "Proteins"])
    confidence: float
    exam_type: ExamType

class TaxonomyClassifier:
    """Multi-label classification against MCAT/USMLE taxonomies."""
    
    def __init__(
        self,
        embedding_model: SentenceTransformer,
        vector_store: WeaviateClient,
        base_threshold: float = 0.65,
        relative_threshold: float = 0.80  # Within 80% of top match
    ):
        self.embeddings = embedding_model
        self.store = vector_store
        self.base_threshold = base_threshold
        self.relative_threshold = relative_threshold
    
    def classify(
        self,
        chunk: Chunk,
        exam_type: ExamType,
        max_topics: int = 5
    ) -> List[TopicMatch]:
        """
        Classify a chunk against the specified taxonomy.
        Uses hybrid search (BM25 + semantic) for robust matching.
        """
        # 1. Generate embedding for chunk
        chunk_embedding = self.embeddings.encode(chunk.text)
        
        # 2. Hybrid search against pre-embedded taxonomy
        collection = f"taxonomy_{exam_type.value}"
        
        results = self.store.query.get(
            collection,
            ["topic_id", "topic_name", "path", "description"]
        ).with_hybrid(
            query=chunk.text,
            vector=chunk_embedding,
            alpha=0.5,  # Balance keyword and semantic
            fusion_type="rankedFusion"
        ).with_limit(max_topics * 2).do()
        
        # 3. Apply dynamic thresholding
        matches = []
        if not results["data"]["Get"][collection]:
            return matches
            
        top_score = results["data"]["Get"][collection][0]["_additional"]["score"]
        dynamic_threshold = max(
            self.base_threshold,
            top_score * self.relative_threshold
        )
        
        for item in results["data"]["Get"][collection]:
            score = item["_additional"]["score"]
            if score >= dynamic_threshold and len(matches) < max_topics:
                matches.append(TopicMatch(
                    topic_id=item["topic_id"],
                    topic_name=item["topic_name"],
                    path=item["path"],
                    confidence=score,
                    exam_type=exam_type
                ))
        
        return matches
    
    def classify_dual(self, chunk: Chunk) -> Dict[ExamType, List[TopicMatch]]:
        """Classify against both MCAT and USMLE taxonomies."""
        return {
            ExamType.MCAT: self.classify(chunk, ExamType.MCAT),
            ExamType.USMLE_STEP1: self.classify(chunk, ExamType.USMLE_STEP1)
        }
```

### 2.3 Generation Layer

The generation layer creates flashcards from classified chunks.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Generation Layer                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      Card Generation Orchestrator                        ││
│  │                                                                          ││
│  │   Classified Chunk ───▶ Strategy Selection ───▶ Parallel Generation     ││
│  │                         (cloze vs vignette)      (async batch)           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│              ┌─────────────────────┼─────────────────────┐                  │
│              ▼                     ▼                     ▼                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  Cloze Generator │  │Vignette Generator│  │ Image Occlusion  │          │
│  │                  │  │                  │  │    Generator     │          │
│  │  - Atomic facts  │  │  - Clinical stem │  │                  │          │
│  │  - 1-3 deletions │  │  - USMLE style   │  │  - Anatomy       │          │
│  │  - Context       │  │  - Diagnosis/Mgmt│  │  - Pathology     │          │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘          │
│           │                     │                     │                     │
│           └─────────────────────┼─────────────────────┘                     │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Validation Pipeline                               ││
│  │                                                                          ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    ││
│  │  │  Schema     │  │  Medical    │  │ Hallucin-   │  │   Quality   │    ││
│  │  │ Validation  │──▶  Accuracy   │──▶  ation      │──▶   Scoring   │    ││
│  │  │             │  │  Check      │  │  Detection  │  │             │    ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Deduplication Service                            ││
│  │                                                                          ││
│  │  - Semantic similarity check against existing cards (threshold: 0.92)   ││
│  │  - Content hash for exact duplicates                                     ││
│  │  - Cross-session persistence via SQLite                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Card Type Decision Logic

```python
class CardTypeStrategy:
    """Determine optimal card type based on content characteristics."""
    
    def select_types(
        self,
        chunk: Chunk,
        topics: List[TopicMatch],
        exam_type: ExamType
    ) -> List[CardType]:
        types = []
        
        # Rule 1: Clinical topics → vignette cards (USMLE only)
        if exam_type in [ExamType.USMLE_STEP1, ExamType.USMLE_STEP2]:
            clinical_disciplines = {"Pathology", "Pharmacology", "Microbiology"}
            if any(t.path[1] in clinical_disciplines for t in topics if len(t.path) > 1):
                types.append(CardType.VIGNETTE)
        
        # Rule 2: Definition/fact-heavy content → cloze
        if self._has_definitions(chunk) or self._has_enumerable_facts(chunk):
            types.append(CardType.CLOZE)
        
        # Rule 3: Images present → image occlusion
        if chunk.has_images:
            types.append(CardType.IMAGE_OCCLUSION)
        
        # Rule 4: Mechanisms/pathways → both cloze and conceptual Q&A
        if self._describes_mechanism(chunk):
            types.extend([CardType.CLOZE, CardType.BASIC_QA])
        
        # Default: always generate cloze cards
        if CardType.CLOZE not in types:
            types.append(CardType.CLOZE)
        
        return types
```

#### LLM Prompt Templates

```python
# Stored in /config/prompts/

CLOZE_GENERATION_PROMPT = """You are a medical education expert creating flashcards for {exam_type}.

Source Content:
{chunk_text}

Topic Context:
- Primary: {primary_topic}
- Related: {related_topics}

Generate {num_cards} cloze deletion flashcards following these rules:

1. MINIMUM INFORMATION PRINCIPLE: One atomic fact per card
2. CLOZE FORMAT: Use {{{{c1::answer}}}} syntax; answers must be 1-4 words
3. CONTEXT: Include enough surrounding text that the card is unambiguous
4. TESTABLE: Focus on concepts likely to appear on {exam_type}, not trivia
5. SELF-CONTAINED: Card must make sense without seeing the source

Output JSON array:
[
  {{
    "text": "The rate-limiting enzyme of glycolysis is {{{{c1::PFK-1}}}}",
    "extra": "Allosterically activated by AMP, inhibited by ATP and citrate",
    "difficulty": "medium"
  }}
]

Generate exactly {num_cards} cards. Ensure each tests a DIFFERENT fact."""

VIGNETTE_GENERATION_PROMPT = """You are creating USMLE-style clinical vignette flashcards.

Source Content:
{chunk_text}

Topic: {primary_topic}
System: {organ_system}
Discipline: {discipline}

Create a clinical vignette card:

FRONT (Clinical Stem):
- Patient demographics (age, sex)
- Setting (ED, clinic, hospital)
- Chief complaint with duration
- 2-3 relevant history/exam findings
- Critical lab or imaging result (if applicable)
- End with: "What is the most likely diagnosis?" OR "What is the most appropriate next step?"

BACK:
1. Answer (1-3 words maximum)
2. Explanation (2-3 sentences connecting presentation → diagnosis)
3. Key distinguishing feature from similar conditions

Output JSON:
{{
  "front": "A 58-year-old man with a history of...",
  "answer": "Acute MI",
  "explanation": "The triad of substernal chest pain, diaphoresis, and ST elevations...",
  "distinguishing_feature": "Unlike unstable angina, troponins are elevated"
}}

Do NOT include multiple choice options - this tests free recall."""
```

#### Validation Pipeline

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import re

class ClozeCard(BaseModel):
    text: str = Field(..., min_length=20, max_length=500)
    extra: Optional[str] = Field(default="", max_length=1000)
    difficulty: str = Field(default="medium")
    source_chunk_id: str
    tags: List[str] = Field(default_factory=list)
    
    @validator("text")
    def validate_cloze_syntax(cls, v):
        # Must contain at least one cloze deletion
        if not re.search(r"\{\{c\d+::[^}]+\}\}", v):
            raise ValueError("Card must contain at least one cloze deletion")
        
        # Cloze answer should be 1-4 words
        cloze_matches = re.findall(r"\{\{c\d+::([^}]+)\}\}", v)
        for match in cloze_matches:
            if len(match.split()) > 4:
                raise ValueError(f"Cloze answer too long: {match}")
        
        return v

class VignetteCard(BaseModel):
    front: str = Field(..., min_length=100, max_length=800)
    answer: str = Field(..., min_length=1, max_length=50)
    explanation: str = Field(..., min_length=50, max_length=500)
    distinguishing_feature: Optional[str] = None
    source_chunk_id: str
    tags: List[str] = Field(default_factory=list)
    
    @validator("front")
    def validate_vignette_structure(cls, v):
        # Must contain patient demographics
        if not re.search(r"\d+-year-old", v):
            raise ValueError("Vignette must include patient age")
        
        # Must end with a question
        if not v.strip().endswith("?"):
            raise ValueError("Vignette must end with a question")
        
        return v

class CardValidator:
    """Multi-stage validation for generated cards."""
    
    def __init__(self, llm_client, medical_kb):
        self.llm = llm_client
        self.kb = medical_kb  # UMLS/First Aid reference
    
    async def validate(self, card: ClozeCard | VignetteCard) -> ValidationResult:
        # Stage 1: Schema validation (handled by Pydantic)
        
        # Stage 2: Medical accuracy check
        accuracy = await self._check_medical_accuracy(card)
        
        # Stage 3: Hallucination detection
        hallucination_score = await self._detect_hallucination(card)
        
        # Stage 4: Quality scoring
        quality = self._compute_quality_score(card, accuracy, hallucination_score)
        
        return ValidationResult(
            is_valid=quality.score >= 0.7,
            accuracy_score=accuracy,
            hallucination_risk=hallucination_score,
            quality_score=quality.score,
            issues=quality.issues
        )
    
    async def _check_medical_accuracy(self, card) -> float:
        """Verify medical facts against knowledge base."""
        # Extract key claims from card
        claims = await self.llm.extract_claims(card.text if hasattr(card, 'text') else card.front)
        
        # Check each claim against UMLS/medical KB
        verified = 0
        for claim in claims:
            if await self.kb.verify_claim(claim):
                verified += 1
        
        return verified / len(claims) if claims else 1.0
    
    async def _detect_hallucination(self, card) -> float:
        """LLM-based hallucination detection."""
        prompt = f"""Evaluate this medical flashcard for factual accuracy.
        
Card: {card.model_dump_json()}

Rate the likelihood of hallucination/inaccuracy from 0.0 (definitely accurate) to 1.0 (likely hallucinated).
Consider: medical terminology usage, plausibility of claims, internal consistency.

Output JSON: {{"score": 0.X, "concerns": ["..."]}}"""
        
        response = await self.llm.generate(prompt, response_model=HallucinationCheck)
        return response.score
```

### 2.4 Export Layer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Export Layer                                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Tag Builder                                      ││
│  │                                                                          ││
│  │  TopicMatches + Source Info ───▶ AnKing-Compatible Hierarchical Tags    ││
│  │                                                                          ││
│  │  MCAT:    #MCAT::Section::FC::Category::Topic                           ││
│  │  USMLE:   #AK_Step1_v12::^Systems::Cardiology::Heart_Failure            ││
│  │           #AK_Step1_v12::#FirstAid::Pathology::Ischemic_HD              ││
│  │           #Source::Lecture::BiochemL05                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      genanki Deck Builder                                ││
│  │                                                                          ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          ││
│  │  │  Model Registry │  │  Deck Manager   │  │  Media Packager │          ││
│  │  │  (Cloze, Basic, │  │  (hierarchy,    │  │  (images,       │          ││
│  │  │   AnKingOverhaul│  │   stable IDs)   │  │   audio clips)  │          ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│              ┌─────────────────────┴─────────────────────┐                  │
│              ▼                                           ▼                  │
│  ┌──────────────────────────┐             ┌──────────────────────────┐     │
│  │     .apkg File Export    │             │   AnkiConnect Live Sync  │     │
│  │                          │             │                          │     │
│  │  - Batch export          │             │  - Real-time card add    │     │
│  │  - Portable file         │             │  - Requires Anki running │     │
│  │  - Import manually       │             │  - localhost:8765        │     │
│  └──────────────────────────┘             └──────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### genanki Models and Deck Structure

```python
import genanki
from hashlib import sha256

# Stable model IDs - NEVER change these after initial deployment
MODEL_IDS = {
    "cloze": 1607392319001,
    "basic": 1607392319002,
    "vignette": 1607392319003,
    "anking_overhaul": 1607392319004,  # Compatible with AnKing deck
}

DECK_IDS = {
    "mcat_master": 2059400110001,
    "usmle_step1": 2059400110002,
    "usmle_step2": 2059400110003,
}

class AnkiModelRegistry:
    """Pre-configured Anki note models."""
    
    @staticmethod
    def get_cloze_model() -> genanki.Model:
        return genanki.Model(
            MODEL_IDS["cloze"],
            "MedAnki Cloze",
            model_type=genanki.Model.CLOZE,
            fields=[
                {"name": "Text"},
                {"name": "Extra"},
                {"name": "Source"},
                {"name": "Lecture"},
            ],
            templates=[{
                "name": "Cloze",
                "qfmt": "{{cloze:Text}}",
                "afmt": """{{cloze:Text}}
                <hr id="extra">
                {{Extra}}
                <div class="source">{{Source}} | {{Lecture}}</div>""",
            }],
            css="""
                .card { font-family: 'Helvetica Neue', Arial; font-size: 18px; 
                        text-align: left; color: #333; background: #fff; }
                .cloze { font-weight: bold; color: #00d; }
                .source { font-size: 12px; color: #888; margin-top: 15px; }
                hr { border: 1px solid #eee; }
            """
        )
    
    @staticmethod
    def get_vignette_model() -> genanki.Model:
        return genanki.Model(
            MODEL_IDS["vignette"],
            "MedAnki Clinical Vignette",
            fields=[
                {"name": "ID"},
                {"name": "Stem"},
                {"name": "Question"},
                {"name": "Answer"},
                {"name": "Explanation"},
                {"name": "Distinguishing"},
                {"name": "Source"},
            ],
            templates=[{
                "name": "Vignette",
                "qfmt": """<div class="stem">{{Stem}}</div>
                          <div class="question"><b>{{Question}}</b></div>""",
                "afmt": """{{FrontSide}}
                          <hr id="answer">
                          <div class="answer">{{Answer}}</div>
                          <div class="explanation">{{Explanation}}</div>
                          <div class="distinguish">💡 {{Distinguishing}}</div>
                          <div class="source">{{Source}}</div>""",
            }],
            css="""
                .card { font-family: 'Helvetica Neue', Arial; font-size: 16px; }
                .stem { line-height: 1.5; }
                .question { margin-top: 15px; color: #0066cc; }
                .answer { font-size: 20px; font-weight: bold; color: #006600; }
                .explanation { margin-top: 10px; }
                .distinguish { margin-top: 10px; background: #ffffd0; padding: 8px; }
                .source { font-size: 12px; color: #888; margin-top: 15px; }
            """
        )

class DeckBuilder:
    """Build and export Anki decks."""
    
    def __init__(self, exam_type: ExamType):
        self.exam_type = exam_type
        self.deck_id = DECK_IDS[f"{exam_type.value}"]
        self.deck = genanki.Deck(self.deck_id, self._deck_name())
        self.media_files = []
        self.models = AnkiModelRegistry()
        
    def _deck_name(self) -> str:
        names = {
            ExamType.MCAT: "MedAnki::MCAT",
            ExamType.USMLE_STEP1: "MedAnki::USMLE::Step1",
            ExamType.USMLE_STEP2: "MedAnki::USMLE::Step2",
        }
        return names[self.exam_type]
    
    def add_cloze_card(self, card: ClozeCard, topics: List[TopicMatch]):
        """Add a cloze deletion card with hierarchical tags."""
        tags = self._build_tags(topics, card.source_chunk_id)
        
        note = genanki.Note(
            model=self.models.get_cloze_model(),
            fields=[card.text, card.extra, card.source_chunk_id, ""],
            tags=tags,
            guid=self._generate_guid(card.text)
        )
        self.deck.add_note(note)
    
    def add_vignette_card(self, card: VignetteCard, topics: List[TopicMatch]):
        """Add a clinical vignette card."""
        tags = self._build_tags(topics, card.source_chunk_id)
        
        # Extract question from stem
        question = card.front.split("?")[0].split(".")[-1].strip() + "?"
        stem = card.front.replace(question, "").strip()
        
        note = genanki.Note(
            model=self.models.get_vignette_model(),
            fields=[
                self._generate_guid(card.front)[:8],
                stem,
                question,
                card.answer,
                card.explanation,
                card.distinguishing_feature or "",
                card.source_chunk_id,
            ],
            tags=tags,
            guid=self._generate_guid(card.front)
        )
        self.deck.add_note(note)
    
    def _build_tags(self, topics: List[TopicMatch], source: str) -> List[str]:
        """Generate AnKing-compatible hierarchical tags."""
        tags = []
        
        for topic in topics[:3]:  # Limit to top 3 topics
            if self.exam_type == ExamType.MCAT:
                # MCAT: #MCAT::Section::FC::Category
                path = "::".join(topic.path)
                tags.append(f"#MCAT::{path}")
            else:
                # USMLE: AnKing-compatible format
                if len(topic.path) >= 2:
                    system = topic.path[0]
                    discipline = topic.path[1] if len(topic.path) > 1 else ""
                    tags.append(f"#AK_Step1_v12::^Systems::{system}")
                    if discipline:
                        tags.append(f"#AK_Step1_v12::#Discipline::{discipline}")
        
        # Source tag
        tags.append(f"#Source::MedAnki::{source}")
        
        return tags
    
    def _generate_guid(self, content: str) -> str:
        """Generate stable GUID from content hash."""
        return sha256(content.encode()).hexdigest()[:20]
    
    def export(self, output_path: str):
        """Export deck to .apkg file."""
        package = genanki.Package(self.deck)
        package.media_files = self.media_files
        package.write_to_file(output_path)
```

---

## 3. Data Models and Schemas

### 3.1 Core Domain Models

```python
# src/medanki/models/domain.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class ContentType(Enum):
    PDF_TEXTBOOK = "pdf_textbook"
    PDF_SLIDES = "pdf_slides"
    PDF_NOTES = "pdf_notes"
    AUDIO_LECTURE = "audio_lecture"
    VIDEO_LECTURE = "video_lecture"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"

class Document(BaseModel):
    """Normalized document representation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    content_type: ContentType
    raw_text: str
    sections: List["Section"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
class Section(BaseModel):
    """Document section with hierarchy."""
    title: str
    level: int  # 1 = chapter, 2 = section, 3 = subsection
    start_char: int
    end_char: int
    page_number: Optional[int] = None

class Chunk(BaseModel):
    """Processed text chunk ready for classification."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    page_number: Optional[int] = None
    section_path: List[str] = Field(default_factory=list)
    entities: List["MedicalEntity"] = Field(default_factory=list)
    embedding: Optional[List[float]] = None

class MedicalEntity(BaseModel):
    """UMLS-linked medical entity."""
    text: str
    label: str  # Entity type (DISEASE, DRUG, ANATOMY, etc.)
    cui: Optional[str] = None  # UMLS Concept Unique Identifier
    start: int
    end: int

class ClassifiedChunk(BaseModel):
    """Chunk with taxonomy classifications."""
    chunk: Chunk
    mcat_topics: List["TopicMatch"] = Field(default_factory=list)
    usmle_topics: List["TopicMatch"] = Field(default_factory=list)
    primary_exam: ExamType

class TopicMatch(BaseModel):
    """Taxonomy topic classification result."""
    topic_id: str
    topic_name: str
    path: List[str]
    confidence: float
    exam_type: ExamType
```

### 3.2 Database Schema (SQLite)

```sql
-- Job tracking and persistence
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    source_path TEXT NOT NULL,
    exam_type TEXT NOT NULL,
    config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Document metadata
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    source_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    metadata_json TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks for resumability
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    text TEXT NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    token_count INTEGER,
    page_number INTEGER,
    section_path_json TEXT,
    entities_json TEXT,
    embedding_id TEXT,  -- Reference to Weaviate vector
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated cards for deduplication
CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES chunks(id),
    card_type TEXT NOT NULL,  -- cloze, vignette, image_occlusion
    content_hash TEXT NOT NULL UNIQUE,  -- For exact duplicate detection
    card_json TEXT NOT NULL,
    tags_json TEXT,
    validation_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deduplication index
CREATE INDEX IF NOT EXISTS idx_cards_content_hash ON cards(content_hash);

-- Taxonomy cache
CREATE TABLE IF NOT EXISTS taxonomy_cache (
    topic_id TEXT PRIMARY KEY,
    exam_type TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    path_json TEXT NOT NULL,
    description TEXT,
    embedding_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 Configuration Schema

```python
# src/medanki/config.py

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path

class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = "anthropic"  # anthropic, openai, local
    model: str = "claude-sonnet-4-5-20250514"
    api_key: Optional[SecretStr] = None
    max_tokens: int = 2048
    temperature: float = 0.3
    max_concurrent_requests: int = 5

class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model_name: str = "neuml/pubmedbert-base-embeddings"
    dimensions: int = 768
    batch_size: int = 32
    device: str = "auto"  # auto, cuda, cpu, mps

class VectorStoreConfig(BaseModel):
    """Weaviate configuration."""
    url: str = "http://localhost:8080"
    grpc_port: int = 50051
    api_key: Optional[SecretStr] = None

class ChunkingConfig(BaseModel):
    """Chunking parameters."""
    target_tokens: int = 450
    max_tokens: int = 512
    overlap_tokens: int = 75
    min_tokens: int = 100

class ClassificationConfig(BaseModel):
    """Taxonomy classification parameters."""
    base_threshold: float = 0.65
    relative_threshold: float = 0.80
    max_topics_per_chunk: int = 5

class GenerationConfig(BaseModel):
    """Card generation parameters."""
    cloze_cards_per_chunk: int = 3
    vignette_probability: float = 0.3
    min_quality_score: float = 0.7
    enable_hallucination_check: bool = True

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    model_config = SettingsConfigDict(
        env_prefix="MEDANKI_",
        env_file=".env",
        env_nested_delimiter="__"
    )
    
    # Data paths
    data_dir: Path = Path("~/.medanki").expanduser()
    cache_dir: Path = Path("~/.medanki/cache").expanduser()
    output_dir: Path = Path("./output")
    
    # Component configs
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    
    # Feature flags
    enable_audio_transcription: bool = True
    enable_image_occlusion: bool = False  # MVP: disabled
    enable_ankiconnect_sync: bool = False
```

---

## 4. API and Interface Design

### 4.1 CLI Interface (Typer)

```python
# src/medanki/cli.py

import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, TaskID

app = typer.Typer(
    name="medanki",
    help="Generate Anki flashcards from medical education materials"
)
console = Console()

@app.command()
def generate(
    input_path: Path = typer.Argument(
        ...,
        help="Path to input file (PDF, audio, markdown) or directory",
        exists=True
    ),
    exam: str = typer.Option(
        "usmle",
        "--exam", "-e",
        help="Target exam: mcat, usmle-step1, usmle-step2"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output .apkg file path (default: <input_name>_cards.apkg)"
    ),
    cards_per_chunk: int = typer.Option(
        3,
        "--cards", "-c",
        help="Target cloze cards per chunk"
    ),
    include_vignettes: bool = typer.Option(
        True,
        "--vignettes/--no-vignettes",
        help="Generate clinical vignette cards (USMLE only)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Process and classify without generating cards"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed progress"
    ),
):
    """
    Generate Anki flashcards from medical education materials.
    
    Examples:
    
        medanki generate lecture.pdf --exam usmle-step1
        
        medanki generate ./lectures/ --exam mcat --output mcat_deck.apkg
        
        medanki generate recording.mp3 --cards 5 --no-vignettes
    """
    from medanki.pipeline import FlashcardPipeline
    from medanki.config import Settings
    
    settings = Settings()
    pipeline = FlashcardPipeline(settings)
    
    with Progress() as progress:
        task = progress.add_task("Processing...", total=100)
        
        result = pipeline.run(
            input_path=input_path,
            exam_type=exam,
            cards_per_chunk=cards_per_chunk,
            include_vignettes=include_vignettes,
            dry_run=dry_run,
            progress_callback=lambda p: progress.update(task, completed=p)
        )
    
    if dry_run:
        console.print(f"[yellow]Dry run complete[/yellow]")
        console.print(f"  Documents: {result.document_count}")
        console.print(f"  Chunks: {result.chunk_count}")
        console.print(f"  Topics matched: {result.topics_matched}")
    else:
        console.print(f"[green]✓[/green] Generated {result.card_count} cards")
        console.print(f"  Output: {result.output_path}")

@app.command()
def init():
    """Initialize MedAnki configuration and data directories."""
    from medanki.setup import initialize_environment
    initialize_environment()
    console.print("[green]✓[/green] MedAnki initialized")

@app.command()
def taxonomy(
    exam: str = typer.Argument(..., help="Exam type: mcat, usmle-step1"),
    action: str = typer.Option("list", "--action", "-a", help="list, update, search"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
):
    """Manage exam taxonomies."""
    from medanki.taxonomy import TaxonomyManager
    
    manager = TaxonomyManager()
    
    if action == "list":
        topics = manager.list_topics(exam)
        for topic in topics[:20]:
            console.print(f"  {topic.path_str}: {topic.name}")
        console.print(f"  ... and {len(topics) - 20} more")
    elif action == "update":
        manager.update_embeddings(exam)
        console.print(f"[green]✓[/green] Updated {exam} taxonomy embeddings")
    elif action == "search" and query:
        results = manager.search(exam, query)
        for r in results:
            console.print(f"  [{r.confidence:.2f}] {r.path_str}")

@app.command()
def sync(
    deck_path: Path = typer.Argument(..., help="Path to .apkg file"),
    deck_name: Optional[str] = typer.Option(None, "--name", "-n", help="Target deck name"),
):
    """Sync cards to Anki via AnkiConnect."""
    from medanki.export import AnkiConnectClient
    
    client = AnkiConnectClient()
    if not client.is_available():
        console.print("[red]Error:[/red] AnkiConnect not available. Is Anki running?")
        raise typer.Exit(1)
    
    result = client.import_deck(deck_path, deck_name)
    console.print(f"[green]✓[/green] Imported {result.cards_added} cards to '{result.deck_name}'")

if __name__ == "__main__":
    app()
```

### 4.2 Internal Service Interfaces

```python
# src/medanki/interfaces.py

from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Optional
from pathlib import Path

class IIngestionService(ABC):
    """Interface for document ingestion."""
    
    @abstractmethod
    async def ingest(self, path: Path) -> Document:
        """Ingest a file and return normalized Document."""
        pass
    
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Return list of supported file extensions."""
        pass

class IChunkingService(ABC):
    """Interface for text chunking."""
    
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """Split document into processable chunks."""
        pass

class IEmbeddingService(ABC):
    """Interface for embedding generation."""
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass
    
    @abstractmethod
    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        pass

class IClassificationService(ABC):
    """Interface for taxonomy classification."""
    
    @abstractmethod
    async def classify(
        self, 
        chunk: Chunk, 
        exam_type: ExamType
    ) -> List[TopicMatch]:
        """Classify chunk against taxonomy."""
        pass

class IGenerationService(ABC):
    """Interface for card generation."""
    
    @abstractmethod
    async def generate_cloze(
        self, 
        chunk: ClassifiedChunk, 
        count: int
    ) -> List[ClozeCard]:
        """Generate cloze deletion cards."""
        pass
    
    @abstractmethod
    async def generate_vignette(
        self, 
        chunk: ClassifiedChunk
    ) -> Optional[VignetteCard]:
        """Generate clinical vignette card."""
        pass

class IValidationService(ABC):
    """Interface for card validation."""
    
    @abstractmethod
    async def validate(
        self, 
        card: ClozeCard | VignetteCard
    ) -> ValidationResult:
        """Validate card quality and accuracy."""
        pass

class IExportService(ABC):
    """Interface for Anki export."""
    
    @abstractmethod
    def build_deck(
        self, 
        cards: List[ClozeCard | VignetteCard],
        exam_type: ExamType
    ) -> Path:
        """Build .apkg file from cards."""
        pass
```

---

## 5. Data Flow Diagrams

### 5.1 End-to-End Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE PIPELINE FLOW                               │
└──────────────────────────────────────────────────────────────────────────────┘

User Input                Processing                    Generation              Export
─────────                 ──────────                    ──────────              ──────

                         ┌─────────────┐
 lecture.pdf ──────────▶ │   Marker    │
                         │  Extractor  │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  Document   │
 recording.mp3 ────────▶ │ Normalizer  │
        │                └──────┬──────┘
        │                       │
        ▼                       │
 ┌─────────────┐               │
 │   Whisper   │───────────────┘
 │ Transcriber │
 └─────────────┘
                         ┌──────▼──────┐
                         │   scispaCy  │
                         │     NER     │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐               ┌─────────────┐
                         │   Medical   │               │  AAMC/NBME  │
                         │   Chunker   │               │  Taxonomy   │
                         │ (450 tokens)│               │  (embedded) │
                         └──────┬──────┘               └──────┬──────┘
                                │                             │
                         ┌──────▼──────┐                      │
                         │ PubMedBERT  │                      │
                         │  Embedder   │                      │
                         └──────┬──────┘                      │
                                │                             │
                                └──────────────┬──────────────┘
                                               │
                                        ┌──────▼──────┐
                                        │   Hybrid    │
                                        │   Search    │
                                        │  (Weaviate) │
                                        └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │  Multi-Label│
                                        │ Classifier  │
                                        │(threshold>0.65)
                                        └──────┬──────┘
                                               │
                       ┌───────────────────────┼───────────────────────┐
                       │                       │                       │
                ┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
                │    Cloze    │         │  Vignette   │         │   Image     │
                │  Generator  │         │  Generator  │         │  Occlusion  │
                │   (Claude)  │         │   (Claude)  │         │ (future)    │
                └──────┬──────┘         └──────┬──────┘         └─────────────┘
                       │                       │
                       └───────────┬───────────┘
                                   │
                            ┌──────▼──────┐
                            │  Validator  │
                            │  Pipeline   │
                            │ (accuracy,  │
                            │ hallucin.)  │
                            └──────┬──────┘
                                   │
                            ┌──────▼──────┐
                            │Deduplicator │
                            │ (semantic + │
                            │    hash)    │
                            └──────┬──────┘
                                   │
                            ┌──────▼──────┐         ┌─────────────┐
                            │   genanki   │────────▶│  deck.apkg  │
                            │   Builder   │         └─────────────┘
                            └──────┬──────┘
                                   │
                                   │ (optional)
                                   ▼
                            ┌─────────────┐
                            │ AnkiConnect │
                            │    Sync     │
                            └─────────────┘
```

### 5.2 Classification Decision Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     TAXONOMY CLASSIFICATION FLOW                              │
└──────────────────────────────────────────────────────────────────────────────┘

                    Chunk: "Beta-blockers reduce myocardial oxygen demand 
                           by decreasing heart rate and contractility..."
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │     BM25 Keyword        │
                              │        Search           │
                              │  query: "beta-blockers  │
                              │   myocardial oxygen     │
                              │   heart rate"           │
                              └───────────┬─────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │              Keyword Matches                 │
                    │  1. Cardiovascular::Pharmacology (0.82)     │
                    │  2. Cardiovascular::Physiology (0.71)       │
                    │  3. Cardiology::Ischemic_HD (0.68)          │
                    │  4. Pulmonology::Bronchodilators (0.41)     │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────────┐
                              │   Semantic Vector       │
                              │      Search             │
                              │  PubMedBERT embedding   │
                              │  cosine similarity      │
                              └───────────┬─────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │              Vector Matches                  │
                    │  1. Cardiovascular::Pharmacology (0.89)     │
                    │  2. Cardiovascular::Physiology (0.84)       │
                    │  3. Cardiology::Heart_Failure (0.77)        │
                    │  4. Autonomic_NS::Sympathetic (0.72)        │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────────┐
                              │    Ranked Fusion        │
                              │    (alpha = 0.5)        │
                              │  Combined scoring       │
                              └───────────┬─────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │              Fused Rankings                  │
                    │  1. Cardiovascular::Pharmacology (0.86)     │
                    │  2. Cardiovascular::Physiology (0.78)       │
                    │  3. Cardiology::Heart_Failure (0.73)        │
                    │  4. Cardiology::Ischemic_HD (0.71)          │
                    │  5. Autonomic_NS::Sympathetic (0.68)        │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────────┐
                              │   Dynamic Threshold     │
                              │                         │
                              │  top = 0.86             │
                              │  threshold = max(       │
                              │    0.65,                │
                              │    0.86 × 0.80 = 0.69)  │
                              │  = 0.69                 │
                              └───────────┬─────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │           FINAL CLASSIFICATIONS              │
                    │                                              │
                    │  ✓ Cardiovascular::Pharmacology (0.86)      │
                    │  ✓ Cardiovascular::Physiology (0.78)        │
                    │  ✓ Cardiology::Heart_Failure (0.73)         │
                    │  ✓ Cardiology::Ischemic_HD (0.71)           │
                    │  ✗ Autonomic_NS::Sympathetic (0.68 < 0.69)  │
                    └─────────────────────────────────────────────┘
                                          │
                                          ▼
                              Tags generated:
                              #AK_Step1_v12::^Systems::Cardiovascular
                              #AK_Step1_v12::#Discipline::Pharmacology
                              #AK_Step1_v12::#Discipline::Physiology
                              #AK_Step1_v12::#FirstAid::Cardiology::Heart_Failure
```

---

## 6. Testing Strategy

### 6.1 Test Architecture

```
tests/
├── unit/
│   ├── test_chunking.py           # Chunker logic
│   ├── test_classification.py     # Threshold logic
│   ├── test_card_validation.py    # Pydantic validation
│   └── test_tag_building.py       # Tag format
├── integration/
│   ├── test_pdf_extraction.py     # Marker integration
│   ├── test_embedding_service.py  # PubMedBERT
│   ├── test_weaviate_search.py    # Vector store
│   └── test_llm_generation.py     # Claude API (VCR)
├── e2e/
│   ├── test_full_pipeline.py      # End-to-end
│   └── test_cli_commands.py       # CLI interface
├── fixtures/
│   ├── sample_pdfs/
│   ├── sample_audio/
│   ├── expected_cards/
│   └── cassettes/                 # VCR recordings
└── conftest.py                    # Shared fixtures
```

### 6.2 Key Test Patterns

```python
# tests/unit/test_card_validation.py

import pytest
from medanki.models import ClozeCard
from pydantic import ValidationError

class TestClozeCardValidation:
    """Test Pydantic validation for cloze cards."""
    
    def test_valid_cloze_card(self):
        card = ClozeCard(
            text="The rate-limiting enzyme of glycolysis is {{c1::PFK-1}}",
            extra="Allosterically regulated",
            source_chunk_id="chunk_123"
        )
        assert "PFK-1" in card.text
    
    def test_missing_cloze_deletion_raises(self):
        with pytest.raises(ValidationError) as exc:
            ClozeCard(
                text="This card has no cloze deletion",
                source_chunk_id="chunk_123"
            )
        assert "must contain at least one cloze deletion" in str(exc.value)
    
    def test_cloze_answer_too_long_raises(self):
        with pytest.raises(ValidationError) as exc:
            ClozeCard(
                text="The enzyme is {{c1::phosphofructokinase-1 which is the rate limiting step}}",
                source_chunk_id="chunk_123"
            )
        assert "Cloze answer too long" in str(exc.value)
    
    @pytest.mark.parametrize("cloze_text,expected_valid", [
        ("{{c1::ATP}} is the energy currency", True),
        ("{{c1::2 ATP}} net yield", True),
        ("{{c1::PFK-1}}, {{c2::hexokinase}}", True),
        ("No cloze here", False),
    ])
    def test_cloze_syntax_variants(self, cloze_text, expected_valid):
        if expected_valid:
            card = ClozeCard(text=cloze_text, source_chunk_id="test")
            assert card is not None
        else:
            with pytest.raises(ValidationError):
                ClozeCard(text=cloze_text, source_chunk_id="test")


# tests/integration/test_llm_generation.py

import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.generate.return_value = {
        "text": '{"text": "{{c1::Mitochondria}} is the powerhouse", "extra": "ATP production"}',
    }
    return client

class TestClozeGeneration:
    """Test LLM-based cloze generation with mocked responses."""
    
    @pytest.mark.vcr  # Record/replay API calls
    async def test_generates_valid_cloze_from_chunk(self, mock_llm_client):
        from medanki.generation import ClozeGenerator
        
        generator = ClozeGenerator(llm_client=mock_llm_client)
        chunk = Chunk(
            text="Mitochondria produce ATP through oxidative phosphorylation...",
            document_id="doc_1",
            start_char=0,
            end_char=100,
            token_count=50
        )
        
        cards = await generator.generate(chunk, count=1)
        
        assert len(cards) == 1
        assert "{{c1::" in cards[0].text


# tests/e2e/test_full_pipeline.py

import pytest
from pathlib import Path
from click.testing import CliRunner
from medanki.cli import app

class TestFullPipeline:
    """End-to-end pipeline tests."""
    
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        # Create minimal test PDF
        pdf_path = tmp_path / "test_lecture.pdf"
        # ... create test PDF
        return pdf_path
    
    @pytest.mark.slow
    def test_pdf_to_apkg_pipeline(self, sample_pdf, tmp_path):
        runner = CliRunner()
        output = tmp_path / "test_output.apkg"
        
        result = runner.invoke(app, [
            "generate",
            str(sample_pdf),
            "--exam", "usmle-step1",
            "--output", str(output),
            "--cards", "2"
        ])
        
        assert result.exit_code == 0
        assert output.exists()
        assert "Generated" in result.output
```

### 6.3 Property-Based Testing for LLM Outputs

```python
# tests/unit/test_generation_properties.py

from hypothesis import given, strategies as st, settings
import pytest

class TestGenerationProperties:
    """Property-based tests for card generation invariants."""
    
    @given(st.text(min_size=100, max_size=1000))
    @settings(max_examples=50)
    def test_cloze_always_has_deletion(self, chunk_text):
        """Any generated cloze card must contain {{c1::...}} syntax."""
        # Mock the LLM response structure
        from medanki.generation import format_cloze_response
        
        # This tests the post-processing, not the LLM itself
        result = format_cloze_response(chunk_text)
        
        if result:  # If generation succeeded
            assert "{{c" in result.text
            assert "}}" in result.text
    
    @given(st.lists(st.text(min_size=10), min_size=1, max_size=10))
    def test_tag_format_consistency(self, topic_paths):
        """Tags must follow hierarchical format."""
        from medanki.export import TagBuilder
        
        builder = TagBuilder(ExamType.USMLE_STEP1)
        topics = [TopicMatch(
            topic_id=f"t{i}",
            topic_name=f"Topic {i}",
            path=path.split("::") if "::" in path else [path],
            confidence=0.8,
            exam_type=ExamType.USMLE_STEP1
        ) for i, path in enumerate(topic_paths)]
        
        tags = builder.build(topics)
        
        for tag in tags:
            assert tag.startswith("#")
            assert "::" in tag or tag.startswith("#Source")
```

---

## 7. Deployment and Operations

### 7.1 Project Structure

```
medanki/
├── pyproject.toml              # uv-managed dependencies
├── .env.example                # Environment template
├── .python-version             # Python version (3.11+)
│
├── src/
│   └── medanki/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI
│       ├── config.py           # Pydantic settings
│       ├── pipeline.py         # Main orchestrator
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── pdf.py          # Marker/Docling
│       │   ├── audio.py        # Whisper
│       │   └── normalizer.py
│       │
│       ├── processing/
│       │   ├── __init__.py
│       │   ├── chunker.py
│       │   ├── embedder.py
│       │   └── classifier.py
│       │
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── cloze.py
│       │   ├── vignette.py
│       │   ├── prompts/
│       │   │   ├── cloze.txt
│       │   │   └── vignette.txt
│       │   └── validator.py
│       │
│       ├── export/
│       │   ├── __init__.py
│       │   ├── deck_builder.py
│       │   ├── models.py       # genanki models
│       │   └── ankiconnect.py
│       │
│       ├── taxonomy/
│       │   ├── __init__.py
│       │   ├── mcat.json       # AAMC outline
│       │   ├── usmle.json      # NBME outline
│       │   └── manager.py
│       │
│       └── storage/
│           ├── __init__.py
│           ├── database.py     # SQLite
│           └── vector.py       # Weaviate client
│
├── tests/                      # As described above
│
├── data/
│   └── taxonomies/             # Pre-embedded taxonomies
│
└── scripts/
    ├── setup_weaviate.py       # Initialize vector DB
    └── embed_taxonomies.py     # Pre-compute embeddings
```

### 7.2 Dependencies (pyproject.toml)

```toml
[project]
name = "medanki"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Core
    "typer>=0.12.0",
    "rich>=13.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    
    # Ingestion
    "marker-pdf>=0.3.0",
    "pymupdf>=1.23.0",
    "openai-whisper>=20231117",
    
    # Processing
    "scispacy>=0.5.4",
    "spacy>=3.7.0",
    "sentence-transformers>=2.3.0",
    
    # Vector store
    "weaviate-client>=4.4.0",
    
    # LLM
    "anthropic>=0.18.0",
    "instructor>=1.0.0",
    
    # Export
    "genanki>=0.13.0",
    
    # Utilities
    "httpx>=0.26.0",
    "aiosqlite>=0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-vcr>=1.0.0",
    "hypothesis>=6.98.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]

[project.scripts]
medanki = "medanki.cli:app"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

### 7.3 Local Services (Docker Compose)

```yaml
# docker-compose.yml

version: '3.8'

services:
  weaviate:
    image: semitechnologies/weaviate:1.24.1
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
      ENABLE_MODULES: ''
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_data:/var/lib/weaviate
    restart: unless-stopped

volumes:
  weaviate_data:
```

---

## 8. MVP vs Full Feature Set

### 8.1 MVP Scope (4-6 weeks)

| Component | MVP Implementation | Deferred |
|-----------|-------------------|----------|
| **Ingestion** | PDF only (Marker) | Audio, video, images |
| **Processing** | Fixed chunking (512 tokens) | Adaptive semantic chunking |
| **Embeddings** | PubMedBERT local | Matryoshka optimization |
| **Classification** | Single taxonomy (USMLE or MCAT) | Dual taxonomy |
| **Generation** | Cloze cards only | Vignettes, image occlusion |
| **Validation** | Schema only | Hallucination detection |
| **Export** | .apkg file | AnkiConnect sync |
| **UI** | CLI only | Web interface |

### 8.2 MVP Implementation Order

```
Week 1: Foundation
├── Project setup (uv, structure)
├── Config system (pydantic-settings)
├── SQLite schema
└── Basic CLI skeleton

Week 2: Ingestion + Processing
├── PDF extraction (Marker)
├── Basic chunking
├── PubMedBERT embedding
└── Weaviate setup

Week 3: Classification
├── Taxonomy JSON loading
├── Pre-embed taxonomies
├── Hybrid search implementation
└── Multi-label classification

Week 4: Generation
├── Claude API integration
├── Cloze prompt engineering
├── Pydantic validation
└── Basic deduplication

Week 5: Export + Polish
├── genanki integration
├── Tag building
├── CLI completion
└── Basic tests

Week 6: Testing + Documentation
├── Integration tests
├── E2E tests
├── README
└── Usage examples
```

---

## 9. Key Design Decisions and Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Vector DB** | Weaviate | Native hybrid search critical for medical abbreviations |
| **Embedding Model** | PubMedBERT | Domain-specific; lower OOV rate than general BERT |
| **PDF Extraction** | Marker (primary) | Best accuracy/speed balance; Docling fallback for tables |
| **LLM** | Claude Sonnet 4 | Strong medical accuracy; structured output support |
| **Chunk Size** | 450-512 tokens | Matches PubMedBERT max; balances context vs precision |
| **Classification Threshold** | 0.65 base, 0.80 relative | Empirically tuned for multi-label assignment |
| **Card Format** | AnKing-compatible | Enables deck interoperability |
| **Storage** | SQLite + Weaviate | Simple local setup; vectors separate from metadata |
| **CLI Framework** | Typer | Modern, type-safe, rich output |

---

## 10. Future Enhancements

### Phase 2 (Post-MVP)
- Audio transcription pipeline (Whisper integration)
- Clinical vignette generation
- Dual taxonomy support (MCAT + USMLE)
- Semantic deduplication
- AnkiConnect live sync

### Phase 3
- Image occlusion generation
- Web interface
- Collaborative deck editing
- AnkiHub integration
- First Aid page linking

### Phase 4
- Video lecture processing
- Lecture timestamp alignment
- UWorld QID matching
- Mobile companion app

---

## Appendix A: Taxonomy JSON Schemas

### MCAT Taxonomy

```json
{
  "exam": "MCAT",
  "version": "2024",
  "sections": [
    {
      "id": "BB",
      "name": "Biological and Biochemical Foundations of Living Systems",
      "foundational_concepts": [
        {
          "id": "FC1",
          "name": "Biomolecules have unique properties...",
          "categories": [
            {
              "id": "1A",
              "name": "Structure and function of proteins",
              "topics": [
                {
                  "id": "1A.1",
                  "name": "Amino Acids",
                  "subtopics": [
                    "Classification",
                    "Absolute configuration",
                    "Dipolar ions"
                  ],
                  "discipline": "BC"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### USMLE Taxonomy

```json
{
  "exam": "USMLE_Step1",
  "version": "2024",
  "systems": [
    {
      "id": "CVS",
      "name": "Cardiovascular System",
      "weight": "7-11%",
      "disciplines": [
        {
          "id": "PATH",
          "name": "Pathology",
          "topics": [
            {
              "id": "CVS-PATH-001",
              "name": "Ischemic Heart Disease",
              "subtopics": [
                "Angina pectoris",
                "Myocardial infarction",
                "Chronic ischemic heart disease"
              ],
              "first_aid_pages": [310, 311, 312]
            }
          ]
        }
      ]
    }
  ]
}
```

---

*Document generated for MedAnki system architecture. Version 1.0.*
