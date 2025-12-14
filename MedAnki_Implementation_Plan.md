# MedAnki Complete Implementation Plan
## From Blank Repo to Production-Ready Application

This document breaks down the entire MedAnki project into **12 phases** with **~60 discrete work chunks**. Each chunk is sized for roughly 2-4 hours of focused work, making it easy to track progress and maintain momentum.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Phase 0: Project Setup & Scaffolding](#phase-0-project-setup--scaffolding)
3. [Phase 1: Core Domain Models & Interfaces](#phase-1-core-domain-models--interfaces)
4. [Phase 2: Shared Services Layer](#phase-2-shared-services-layer)
5. [Phase 3: Ingestion Layer](#phase-3-ingestion-layer)
6. [Phase 4: Processing Layer - Chunking](#phase-4-processing-layer---chunking)
7. [Phase 5: Processing Layer - Embeddings & Vector Store](#phase-5-processing-layer---embeddings--vector-store)
8. [Phase 6: Processing Layer - Classification](#phase-6-processing-layer---classification)
9. [Phase 7: Generation Layer](#phase-7-generation-layer)
10. [Phase 8: Export Layer](#phase-8-export-layer)
11. [Phase 9: CLI Interface](#phase-9-cli-interface)
12. [Phase 10: FastAPI Backend](#phase-10-fastapi-backend)
13. [Phase 11: React Frontend](#phase-11-react-frontend)
14. [Phase 12: Integration, Testing & Deployment](#phase-12-integration-testing--deployment)
15. [Dependency Graph](#dependency-graph)
16. [Timeline Estimates](#timeline-estimates)

---

## Project Overview

### Final Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interfaces                                 │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │     CLI (Typer + Rich)      │    │   Web (React + FastAPI)             │ │
│  └─────────────────────────────┘    └─────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│                              MedAnki Core                                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                │
│  │ Ingestion │──│ Processing│──│ Generation│──│  Export   │                │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘                │
│                              Shared Services                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                │
│  │  Config   │  │ Taxonomy  │  │    LLM    │  │   Cache   │                │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘                │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Data Layer                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐      │
│  │    Weaviate     │  │     SQLite      │  │     File System         │      │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Repository Structure (End State)

```
medanki/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.web
│   └── docker-compose.yml
├── packages/
│   ├── core/                    # MedAnki core library
│   │   ├── pyproject.toml
│   │   └── src/medanki/
│   │       ├── __init__.py
│   │       ├── models/          # Domain models
│   │       ├── ingestion/       # PDF, audio, text extraction
│   │       ├── processing/      # Chunking, embedding, classification
│   │       ├── generation/      # Card generation, validation
│   │       ├── export/          # genanki, AnkiConnect
│   │       ├── services/        # Config, taxonomy, LLM, cache
│   │       └── storage/         # SQLite, Weaviate adapters
│   ├── cli/                     # CLI application
│   │   ├── pyproject.toml
│   │   └── src/medanki_cli/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       └── commands/
│   └── api/                     # FastAPI backend
│       ├── pyproject.toml
│       └── src/medanki_api/
│           ├── __init__.py
│           ├── main.py
│           ├── routes/
│           ├── websocket/
│           └── schemas/
├── web/                         # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── api/
│       └── stores/
├── data/
│   ├── taxonomies/
│   │   ├── mcat.json
│   │   └── usmle_step1.json
│   └── test_fixtures/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
├── pyproject.toml               # Workspace root
├── README.md
└── Makefile
```

---

## Phase 0: Project Setup & Scaffolding

**Goal:** Empty repo → runnable project skeleton with all tooling configured.

### Chunk 0.1: Repository Initialization
**Time:** 1 hour  
**Dependencies:** None  
**Deliverables:**
- [ ] Create GitHub repository
- [ ] Initialize with README.md, .gitignore (Python + Node)
- [ ] Add MIT LICENSE
- [ ] Create branch protection rules (main)
- [ ] Set up issue templates

**Commands:**
```bash
mkdir medanki && cd medanki
git init
echo "# MedAnki" > README.md
curl -o .gitignore https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore
echo "\n# Node\nnode_modules/\ndist/\n.env.local" >> .gitignore
```

---

### Chunk 0.2: Python Monorepo Setup
**Time:** 2 hours  
**Dependencies:** 0.1  
**Deliverables:**
- [ ] Install uv package manager
- [ ] Create workspace pyproject.toml
- [ ] Create packages/core, packages/cli, packages/api structure
- [ ] Configure shared dev dependencies (pytest, ruff, mypy)
- [ ] Add Makefile with common commands

**Files to create:**

```toml
# pyproject.toml (workspace root)
[project]
name = "medanki-workspace"
version = "0.1.0"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
medanki = { workspace = true }
medanki-cli = { workspace = true }
medanki-api = { workspace = true }

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```toml
# packages/core/pyproject.toml
[project]
name = "medanki"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiosqlite>=0.19.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
ingestion = ["marker-pdf", "pymupdf"]
processing = ["sentence-transformers", "weaviate-client>=4.4.0"]
generation = ["anthropic>=0.18.0", "instructor>=1.0.0"]
export = ["genanki>=0.13.0"]
nlp = ["scispacy>=0.5.4", "spacy>=3.7.0"]
all = ["medanki[ingestion,processing,generation,export,nlp]"]
dev = ["pytest>=8.0", "pytest-asyncio", "hypothesis", "ruff", "mypy"]
```

```makefile
# Makefile
.PHONY: install test lint format

install:
	uv sync --all-extras

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run mypy packages/

format:
	uv run ruff format .

dev-core:
	uv run pytest tests/unit -v --tb=short

dev-api:
	uv run uvicorn medanki_api.main:app --reload --port 8000

dev-web:
	cd web && npm run dev
```

---

### Chunk 0.3: React Frontend Scaffolding
**Time:** 1.5 hours  
**Dependencies:** 0.1  
**Deliverables:**
- [ ] Initialize Vite + React + TypeScript project
- [ ] Add Tailwind CSS
- [ ] Add React Query for data fetching
- [ ] Add React Router for navigation
- [ ] Add Zustand for state management
- [ ] Configure ESLint + Prettier

**Commands:**
```bash
cd medanki
npm create vite@latest web -- --template react-ts
cd web
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install @tanstack/react-query react-router-dom zustand
npm install -D @types/react-router-dom eslint prettier
```

**Files:**
```typescript
// web/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
```

---

### Chunk 0.4: Docker & Local Services Setup
**Time:** 1.5 hours  
**Dependencies:** 0.2  
**Deliverables:**
- [ ] Create docker-compose.yml for Weaviate
- [ ] Create Dockerfile.api for FastAPI
- [ ] Create Dockerfile.web for React (nginx)
- [ ] Add docker-compose.dev.yml for development
- [ ] Test Weaviate connection

**Files:**
```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  weaviate:
    image: semitechnologies/weaviate:1.24.1
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      QUERY_DEFAULTS_LIMIT: 25
      DEFAULT_VECTORIZER_MODULE: 'none'
    volumes:
      - weaviate_data:/var/lib/weaviate

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - WEAVIATE_URL=http://weaviate:8080
    depends_on:
      - weaviate
    volumes:
      - ../data:/app/data
      - uploads:/app/uploads

  web:
    build:
      context: ../web
      dockerfile: ../docker/Dockerfile.web
    ports:
      - "3000:80"
    depends_on:
      - api

volumes:
  weaviate_data:
  uploads:
```

---

### Chunk 0.5: CI/CD Pipeline Setup
**Time:** 1 hour  
**Dependencies:** 0.2, 0.3  
**Deliverables:**
- [ ] GitHub Actions workflow for Python tests
- [ ] GitHub Actions workflow for React build
- [ ] Pre-commit hooks configuration
- [ ] Dependabot configuration

**Files:**
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run pytest tests/unit -v

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd web && npm ci
      - run: cd web && npm run lint
      - run: cd web && npm run build
```

---

### Chunk 0.6: Environment & Configuration
**Time:** 1 hour  
**Dependencies:** 0.2  
**Deliverables:**
- [ ] Create .env.example with all variables
- [ ] Create packages/core/src/medanki/config.py with pydantic-settings
- [ ] Add environment validation on startup
- [ ] Document all configuration options

**Files:**
```bash
# .env.example
# Required
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Optional - Weaviate (defaults to local Docker)
WEAVIATE_URL=http://localhost:8080
# WEAVIATE_API_KEY=  # Only for cloud

# Optional - Feature flags
MEDANKI_ENABLE_VIGNETTES=true
MEDANKI_ENABLE_HALLUCINATION_CHECK=true
MEDANKI_MAX_CARDS_PER_CHUNK=5

# Optional - Development
MEDANKI_DEBUG=false
MEDANKI_LOG_LEVEL=INFO
```

```python
# packages/core/src/medanki/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDANKI_",
        env_file=".env",
        extra="ignore"
    )
    
    # Required
    anthropic_api_key: str
    
    # Weaviate
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str | None = None
    
    # Feature flags
    enable_vignettes: bool = True
    enable_hallucination_check: bool = True
    max_cards_per_chunk: int = 5
    
    # Processing
    chunk_size: int = 512
    chunk_overlap: int = 75
    classification_threshold: float = 0.65
    
    # Development
    debug: bool = False
    log_level: str = "INFO"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Phase 1: Core Domain Models & Interfaces

**Goal:** Define all data structures and service contracts that the rest of the system will use.

### Chunk 1.1: Enumerations & Constants
**Time:** 1 hour  
**Dependencies:** 0.2  
**Deliverables:**
- [ ] ExamType enum (MCAT, USMLE_STEP1, USMLE_STEP2)
- [ ] ContentType enum (PDF_TEXTBOOK, AUDIO_LECTURE, etc.)
- [ ] CardType enum (CLOZE, VIGNETTE, BASIC_QA)
- [ ] ValidationStatus enum
- [ ] Constants module (model IDs, paths, limits)

**File:** `packages/core/src/medanki/models/enums.py`

---

### Chunk 1.2: Document & Section Models
**Time:** 1.5 hours  
**Dependencies:** 1.1  
**Deliverables:**
- [ ] Document dataclass with validation
- [ ] Section dataclass
- [ ] MedicalEntity dataclass with UMLS fields
- [ ] Metadata schema
- [ ] Unit tests for serialization

**File:** `packages/core/src/medanki/models/document.py`

**Tests:** `tests/unit/models/test_document.py`

---

### Chunk 1.3: Chunk & Classification Models
**Time:** 1.5 hours  
**Dependencies:** 1.2  
**Deliverables:**
- [ ] Chunk dataclass
- [ ] TopicMatch dataclass
- [ ] ClassifiedChunk dataclass
- [ ] ChunkMetadata for provenance tracking
- [ ] Unit tests

**File:** `packages/core/src/medanki/models/chunk.py`

---

### Chunk 1.4: Card Models with Validation
**Time:** 2 hours  
**Dependencies:** 1.1  
**Deliverables:**
- [ ] ClozeCard model with cloze syntax validator
- [ ] VignetteCard model with structure validators
- [ ] ValidationResult model
- [ ] Card factory functions
- [ ] Comprehensive unit tests for validators

**File:** `packages/core/src/medanki/models/cards.py`

**Key validation:**
```python
from pydantic import BaseModel, field_validator
import re

class ClozeCard(BaseModel):
    id: str
    text: str
    extra: str = ""
    tags: list[str] = []
    source_chunk_id: str
    
    @field_validator("text")
    @classmethod
    def validate_cloze_syntax(cls, v: str) -> str:
        pattern = r"\{\{c\d+::[^}]+\}\}"
        if not re.search(pattern, v):
            raise ValueError("Text must contain valid cloze deletion {{c1::...}}")
        return v
    
    @field_validator("text")
    @classmethod
    def validate_cloze_answer_length(cls, v: str) -> str:
        answers = re.findall(r"\{\{c\d+::([^}]+)\}\}", v)
        for answer in answers:
            if len(answer.split()) > 4:
                raise ValueError(f"Cloze answer too long: {answer}")
        return v
```

---

### Chunk 1.5: Service Interfaces (Protocols)
**Time:** 2 hours  
**Dependencies:** 1.2, 1.3, 1.4  
**Deliverables:**
- [ ] IIngestionService protocol
- [ ] IChunkingService protocol
- [ ] IEmbeddingService protocol
- [ ] IClassificationService protocol
- [ ] IGenerationService protocol
- [ ] IValidationService protocol
- [ ] IExportService protocol
- [ ] IVectorStore protocol
- [ ] ITaxonomyService protocol

**File:** `packages/core/src/medanki/services/protocols.py`

---

### Chunk 1.6: Result Types & Errors
**Time:** 1 hour  
**Dependencies:** 1.4  
**Deliverables:**
- [ ] GenerationResult dataclass
- [ ] ProcessingResult dataclass
- [ ] Custom exception hierarchy (MedAnkiError, ValidationError, etc.)
- [ ] Error codes enum

**File:** `packages/core/src/medanki/models/results.py`, `packages/core/src/medanki/exceptions.py`

---

## Phase 2: Shared Services Layer

**Goal:** Implement cross-cutting services used by all layers.

### Chunk 2.1: Configuration Service
**Time:** 1.5 hours  
**Dependencies:** 0.6, 1.5  
**Deliverables:**
- [ ] Singleton config manager
- [ ] Environment-specific overrides
- [ ] Config validation on startup
- [ ] Hot-reload support (for dev)

**File:** `packages/core/src/medanki/services/config.py`

---

### Chunk 2.2: Taxonomy Service - Schema & Loading
**Time:** 2 hours  
**Dependencies:** 1.3  
**Deliverables:**
- [ ] MCAT taxonomy JSON schema
- [ ] USMLE Step 1 taxonomy JSON schema
- [ ] Taxonomy loader with validation
- [ ] Topic tree data structure
- [ ] Tests with sample taxonomy data

**Files:** 
- `packages/core/src/medanki/services/taxonomy.py`
- `data/taxonomies/mcat.json`
- `data/taxonomies/usmle_step1.json`

---

### Chunk 2.3: Taxonomy Service - Embeddings
**Time:** 2 hours  
**Dependencies:** 2.2, 5.1  
**Deliverables:**
- [ ] Pre-embed all taxonomy topics
- [ ] Cache embeddings to disk
- [ ] Lazy loading of embeddings
- [ ] Invalidation on taxonomy change

**File:** `packages/core/src/medanki/services/taxonomy.py` (extend)

---

### Chunk 2.4: LLM Client Abstraction
**Time:** 2.5 hours  
**Dependencies:** 0.6, 1.5  
**Deliverables:**
- [ ] Abstract LLM client interface
- [ ] Anthropic (Claude) implementation
- [ ] Structured output support with Instructor
- [ ] Retry logic with exponential backoff
- [ ] Token counting and cost tracking
- [ ] Tests with mocked responses

**File:** `packages/core/src/medanki/services/llm.py`

```python
# Key structure
from abc import ABC, abstractmethod
from anthropic import Anthropic
import instructor

class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...
    
    @abstractmethod
    async def generate_structured[T](
        self, prompt: str, response_model: type[T], **kwargs
    ) -> T: ...

class ClaudeClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250514"):
        self._client = instructor.from_anthropic(Anthropic(api_key=api_key))
        self._model = model
    
    async def generate_structured[T](
        self, prompt: str, response_model: type[T], **kwargs
    ) -> T:
        return await self._client.messages.create(
            model=self._model,
            response_model=response_model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=[{"role": "user", "content": prompt}],
            max_retries=3
        )
```

---

### Chunk 2.5: Cache Layer
**Time:** 1.5 hours  
**Dependencies:** 1.5  
**Deliverables:**
- [ ] Cache interface
- [ ] In-memory cache implementation
- [ ] Disk cache implementation (for embeddings)
- [ ] TTL and size limits
- [ ] Cache key generation utilities

**File:** `packages/core/src/medanki/services/cache.py`

---

### Chunk 2.6: SQLite Storage Adapter
**Time:** 2 hours  
**Dependencies:** 1.2, 1.3, 1.4  
**Deliverables:**
- [ ] Database schema (jobs, documents, chunks, cards)
- [ ] Async SQLite connection pool
- [ ] Repository pattern for each entity
- [ ] Migration support
- [ ] Tests with in-memory SQLite

**File:** `packages/core/src/medanki/storage/sqlite.py`

```sql
-- Schema
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    exam_type TEXT NOT NULL,
    config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    source_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    raw_text TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(id),
    text TEXT NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    token_count INTEGER,
    embedding_id TEXT,
    topics_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    chunk_id TEXT REFERENCES chunks(id),
    card_type TEXT NOT NULL,
    content_json TEXT NOT NULL,
    content_hash TEXT UNIQUE,
    validation_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 3: Ingestion Layer

**Goal:** Extract text from various input formats.

### Chunk 3.1: PDF Extractor - Marker Integration
**Time:** 3 hours  
**Dependencies:** 1.2  
**Deliverables:**
- [ ] MarkerExtractor class
- [ ] Section detection from markdown headers
- [ ] Page number extraction
- [ ] Table handling
- [ ] Tests with sample PDFs

**File:** `packages/core/src/medanki/ingestion/pdf.py`

---

### Chunk 3.2: PDF Extractor - Fallbacks
**Time:** 2 hours  
**Dependencies:** 3.1  
**Deliverables:**
- [ ] PyMuPDF4LLM extractor for speed
- [ ] Docling extractor for complex tables
- [ ] PDF analysis for strategy selection
- [ ] Unified interface

**File:** `packages/core/src/medanki/ingestion/pdf.py` (extend)

---

### Chunk 3.3: Text & Markdown Ingestion
**Time:** 1 hour  
**Dependencies:** 1.2  
**Deliverables:**
- [ ] Plain text loader
- [ ] Markdown parser with section extraction
- [ ] Front matter handling
- [ ] Tests

**File:** `packages/core/src/medanki/ingestion/text.py`

---

### Chunk 3.4: Audio Transcription (Deferred to Phase 2)
**Time:** 3 hours  
**Dependencies:** 1.2  
**Deliverables:**
- [ ] Whisper integration (local or API)
- [ ] Word-level timestamps
- [ ] Segment detection by pauses
- [ ] Speaker diarization (optional)

**File:** `packages/core/src/medanki/ingestion/audio.py`

**Note:** Mark as optional for MVP; can be added in Phase 2.

---

### Chunk 3.5: Document Normalizer
**Time:** 1.5 hours  
**Dependencies:** 3.1, 3.2, 3.3  
**Deliverables:**
- [ ] Unified Document factory
- [ ] Content type detection
- [ ] Metadata extraction
- [ ] Source path normalization

**File:** `packages/core/src/medanki/ingestion/normalizer.py`

---

### Chunk 3.6: Ingestion Service Facade
**Time:** 1.5 hours  
**Dependencies:** 3.5  
**Deliverables:**
- [ ] IngestionService implementing IIngestionService
- [ ] File type routing
- [ ] Batch ingestion support
- [ ] Progress callbacks
- [ ] Integration tests

**File:** `packages/core/src/medanki/ingestion/service.py`

---

## Phase 4: Processing Layer - Chunking

**Goal:** Split documents into embeddable chunks with medical term preservation.

### Chunk 4.1: Basic Chunker
**Time:** 2 hours  
**Dependencies:** 1.3  
**Deliverables:**
- [ ] Token-based chunking
- [ ] Configurable chunk size and overlap
- [ ] Tokenizer integration (tiktoken or HF)
- [ ] Basic tests

**File:** `packages/core/src/medanki/processing/chunker.py`

---

### Chunk 4.2: Section-Aware Chunking
**Time:** 2 hours  
**Dependencies:** 4.1  
**Deliverables:**
- [ ] Prefer section boundaries
- [ ] Header hierarchy tracking
- [ ] Section path in chunk metadata
- [ ] Tests with structured documents

**File:** `packages/core/src/medanki/processing/chunker.py` (extend)

---

### Chunk 4.3: Medical Term Preservation
**Time:** 2.5 hours  
**Dependencies:** 4.1  
**Deliverables:**
- [ ] Protected terms list (drug names, anatomy)
- [ ] Lab value regex patterns
- [ ] Never-split rules
- [ ] Integration with scispaCy NER
- [ ] Tests with edge cases

**File:** `packages/core/src/medanki/processing/chunker.py` (extend)

```python
# Key patterns to protect
PROTECTED_PATTERNS = [
    r"\d+\.?\d*\s*(mg|mcg|g|mL|L|mEq|mmol|ng|IU)/\s*(dL|L|mL|kg|min|hr|day)",  # Lab values
    r"[A-Z][a-z]+\s+(acid|oxide|chloride|sulfate|phosphate)",  # Chemical compounds
    r"(left|right)\s+(anterior|posterior|lateral|medial)\s+\w+",  # Anatomical terms
]
```

---

### Chunk 4.4: Entity Extraction Integration
**Time:** 2 hours  
**Dependencies:** 4.1  
**Deliverables:**
- [ ] scispaCy NER pipeline
- [ ] Entity attachment to chunks
- [ ] UMLS linking (optional)
- [ ] Abbreviation detection
- [ ] Tests

**File:** `packages/core/src/medanki/processing/entities.py`

---

### Chunk 4.5: Chunking Service Facade
**Time:** 1 hour  
**Dependencies:** 4.1, 4.2, 4.3, 4.4  
**Deliverables:**
- [ ] ChunkingService implementing IChunkingService
- [ ] Configuration-driven behavior
- [ ] Batch processing support

**File:** `packages/core/src/medanki/processing/chunking_service.py`

---

## Phase 5: Processing Layer - Embeddings & Vector Store

**Goal:** Generate and store embeddings for semantic search.

### Chunk 5.1: PubMedBERT Embedder
**Time:** 2 hours  
**Dependencies:** 1.5  
**Deliverables:**
- [ ] SentenceTransformer wrapper
- [ ] Batch embedding with progress
- [ ] GPU/CPU auto-detection
- [ ] Embedding cache
- [ ] Tests

**File:** `packages/core/src/medanki/processing/embedder.py`

---

### Chunk 5.2: Weaviate Client Setup
**Time:** 2 hours  
**Dependencies:** 0.4  
**Deliverables:**
- [ ] Weaviate connection manager
- [ ] Schema creation (MedicalChunk collection)
- [ ] Health check
- [ ] Connection pooling

**File:** `packages/core/src/medanki/storage/weaviate.py`

---

### Chunk 5.3: Vector Store Operations
**Time:** 2.5 hours  
**Dependencies:** 5.2  
**Deliverables:**
- [ ] Upsert with metadata
- [ ] Pure vector search
- [ ] BM25 keyword search
- [ ] Hybrid search with alpha
- [ ] Batch operations
- [ ] Tests with Docker Weaviate

**File:** `packages/core/src/medanki/storage/weaviate.py` (extend)

---

### Chunk 5.4: Embedding Service Facade
**Time:** 1.5 hours  
**Dependencies:** 5.1, 5.3  
**Deliverables:**
- [ ] EmbeddingService implementing IEmbeddingService
- [ ] Automatic storage after embedding
- [ ] Retrieval by ID

**File:** `packages/core/src/medanki/processing/embedding_service.py`

---

## Phase 6: Processing Layer - Classification

**Goal:** Match chunks to taxonomy topics using hybrid search.

### Chunk 6.1: Taxonomy Matcher
**Time:** 2.5 hours  
**Dependencies:** 2.2, 2.3, 5.3  
**Deliverables:**
- [ ] Hybrid search against taxonomy embeddings
- [ ] BM25 component for abbreviations
- [ ] Score combination (alpha weighting)
- [ ] Tests with known mappings

**File:** `packages/core/src/medanki/processing/classifier.py`

---

### Chunk 6.2: Multi-Label Classification
**Time:** 2 hours  
**Dependencies:** 6.1  
**Deliverables:**
- [ ] Dynamic threshold calculation
- [ ] Top-K selection
- [ ] Confidence calibration
- [ ] Tests for edge cases

**File:** `packages/core/src/medanki/processing/classifier.py` (extend)

---

### Chunk 6.3: Dual Taxonomy Support
**Time:** 1.5 hours  
**Dependencies:** 6.2  
**Deliverables:**
- [ ] Classify against both MCAT and USMLE
- [ ] Primary exam detection
- [ ] Parallel classification
- [ ] Result merging

**File:** `packages/core/src/medanki/processing/classifier.py` (extend)

---

### Chunk 6.4: Classification Service Facade
**Time:** 1 hour  
**Dependencies:** 6.3  
**Deliverables:**
- [ ] ClassificationService implementing IClassificationService
- [ ] Batch classification
- [ ] Progress callbacks

**File:** `packages/core/src/medanki/processing/classification_service.py`

---

## Phase 7: Generation Layer

**Goal:** Generate flashcards from classified chunks using LLMs.

### Chunk 7.1: Cloze Generation Prompts
**Time:** 2.5 hours  
**Dependencies:** 2.4, 1.4  
**Deliverables:**
- [ ] Cloze generation prompt template
- [ ] Few-shot examples
- [ ] Topic-specific variations (pharm, anatomy)
- [ ] Output parsing
- [ ] Tests with mocked LLM

**File:** `packages/core/src/medanki/generation/cloze.py`

---

### Chunk 7.2: Vignette Generation Prompts
**Time:** 2.5 hours  
**Dependencies:** 2.4, 1.4  
**Deliverables:**
- [ ] Vignette generation prompt template
- [ ] Demographics generation
- [ ] Question type selection
- [ ] Output parsing
- [ ] Tests

**File:** `packages/core/src/medanki/generation/vignette.py`

---

### Chunk 7.3: Card Validator - Schema
**Time:** 1.5 hours  
**Dependencies:** 1.4  
**Deliverables:**
- [ ] Cloze syntax validation
- [ ] Answer length validation
- [ ] Vignette structure validation
- [ ] Validation result generation

**File:** `packages/core/src/medanki/generation/validator.py`

---

### Chunk 7.4: Card Validator - Medical Accuracy
**Time:** 2.5 hours  
**Dependencies:** 7.3, 2.4  
**Deliverables:**
- [ ] Claim extraction from cards
- [ ] LLM-based fact checking
- [ ] Confidence scoring
- [ ] Tests with known correct/incorrect cards

**File:** `packages/core/src/medanki/generation/validator.py` (extend)

---

### Chunk 7.5: Hallucination Detection
**Time:** 2 hours  
**Dependencies:** 7.4  
**Deliverables:**
- [ ] Source chunk comparison
- [ ] Entity verification
- [ ] Hallucination risk scoring
- [ ] Tests

**File:** `packages/core/src/medanki/generation/validator.py` (extend)

---

### Chunk 7.6: Deduplication
**Time:** 2 hours  
**Dependencies:** 5.1  
**Deliverables:**
- [ ] Content hash for exact duplicates
- [ ] Semantic similarity check
- [ ] Cross-session persistence (SQLite)
- [ ] Duplicate marking vs removal

**File:** `packages/core/src/medanki/generation/deduplicator.py`

---

### Chunk 7.7: Generation Service Facade
**Time:** 2 hours  
**Dependencies:** 7.1-7.6  
**Deliverables:**
- [ ] GenerationService implementing IGenerationService
- [ ] Pipeline: generate → validate → dedupe
- [ ] Batch generation
- [ ] Progress callbacks
- [ ] Integration tests

**File:** `packages/core/src/medanki/generation/service.py`

---

## Phase 8: Export Layer

**Goal:** Package cards into Anki-compatible formats.

### Chunk 8.1: Tag Builder
**Time:** 2 hours  
**Dependencies:** 1.3  
**Deliverables:**
- [ ] Hierarchical tag generation
- [ ] AnKing format compatibility
- [ ] MCAT vs USMLE tag patterns
- [ ] Source tagging
- [ ] Tests

**File:** `packages/core/src/medanki/export/tags.py`

---

### Chunk 8.2: Genanki Model Registry
**Time:** 2 hours  
**Dependencies:** 1.4  
**Deliverables:**
- [ ] Stable model IDs
- [ ] Cloze model definition
- [ ] Vignette (Basic) model definition
- [ ] CSS styling
- [ ] Model versioning

**File:** `packages/core/src/medanki/export/models.py`

---

### Chunk 8.3: Deck Builder
**Time:** 2.5 hours  
**Dependencies:** 8.1, 8.2  
**Deliverables:**
- [ ] Stable deck IDs
- [ ] GUID generation (content-based)
- [ ] Note creation from cards
- [ ] Hierarchical deck naming
- [ ] Media handling
- [ ] Tests

**File:** `packages/core/src/medanki/export/deck.py`

---

### Chunk 8.4: APKG Exporter
**Time:** 1.5 hours  
**Dependencies:** 8.3  
**Deliverables:**
- [ ] Package creation
- [ ] File writing
- [ ] Temp file cleanup
- [ ] Integration tests

**File:** `packages/core/src/medanki/export/apkg.py`

---

### Chunk 8.5: AnkiConnect Integration (Optional)
**Time:** 2 hours  
**Dependencies:** 8.3  
**Deliverables:**
- [ ] AnkiConnect client
- [ ] Deck sync
- [ ] Note sync with duplicate handling
- [ ] Connection detection

**File:** `packages/core/src/medanki/export/ankiconnect.py`

---

### Chunk 8.6: Export Service Facade
**Time:** 1.5 hours  
**Dependencies:** 8.4, 8.5  
**Deliverables:**
- [ ] ExportService implementing IExportService
- [ ] Format selection (apkg vs ankiconnect)
- [ ] Batch export

**File:** `packages/core/src/medanki/export/service.py`

---

## Phase 9: CLI Interface

**Goal:** Command-line interface for the core library.

### Chunk 9.1: CLI Skeleton
**Time:** 1.5 hours  
**Dependencies:** Phase 2-8  
**Deliverables:**
- [ ] Typer app initialization
- [ ] Global options (--verbose, --config)
- [ ] Help text
- [ ] Version command

**File:** `packages/cli/src/medanki_cli/main.py`

---

### Chunk 9.2: Generate Command
**Time:** 2.5 hours  
**Dependencies:** 9.1  
**Deliverables:**
- [ ] `medanki generate <input> --exam --output --cards`
- [ ] Progress bar with Rich
- [ ] Summary output
- [ ] Error handling

**File:** `packages/cli/src/medanki_cli/commands/generate.py`

---

### Chunk 9.3: Taxonomy Commands
**Time:** 1.5 hours  
**Dependencies:** 9.1, 2.2  
**Deliverables:**
- [ ] `medanki taxonomy list`
- [ ] `medanki taxonomy search <query>`
- [ ] `medanki taxonomy update`
- [ ] Tree visualization

**File:** `packages/cli/src/medanki_cli/commands/taxonomy.py`

---

### Chunk 9.4: Init & Config Commands
**Time:** 1 hour  
**Dependencies:** 9.1  
**Deliverables:**
- [ ] `medanki init` - create config files
- [ ] `medanki config show`
- [ ] `medanki config set <key> <value>`

**File:** `packages/cli/src/medanki_cli/commands/config.py`

---

### Chunk 9.5: CLI Integration Tests
**Time:** 2 hours  
**Dependencies:** 9.2-9.4  
**Deliverables:**
- [ ] E2E test: PDF → .apkg
- [ ] Test with fixtures
- [ ] Error case tests

**File:** `tests/e2e/test_cli.py`

---

## Phase 10: FastAPI Backend

**Goal:** REST API with WebSocket support for the web interface.

### Chunk 10.1: FastAPI App Setup
**Time:** 1.5 hours  
**Dependencies:** 0.6  
**Deliverables:**
- [ ] FastAPI app initialization
- [ ] CORS configuration
- [ ] Exception handlers
- [ ] Health check endpoint
- [ ] OpenAPI customization

**File:** `packages/api/src/medanki_api/main.py`

---

### Chunk 10.2: API Schemas (Pydantic)
**Time:** 2 hours  
**Dependencies:** 10.1, 1.2-1.4  
**Deliverables:**
- [ ] Request schemas (UploadRequest, etc.)
- [ ] Response schemas (JobResponse, etc.)
- [ ] Shared with frontend via OpenAPI
- [ ] Validation tests

**File:** `packages/api/src/medanki_api/schemas/`

---

### Chunk 10.3: Upload Endpoint
**Time:** 2 hours  
**Dependencies:** 10.2  
**Deliverables:**
- [ ] POST /api/upload
- [ ] File validation (type, size)
- [ ] Job creation
- [ ] Background task trigger
- [ ] Tests

**File:** `packages/api/src/medanki_api/routes/upload.py`

---

### Chunk 10.4: Job Status Endpoint
**Time:** 1.5 hours  
**Dependencies:** 10.2, 2.6  
**Deliverables:**
- [ ] GET /api/jobs/{job_id}
- [ ] Status polling
- [ ] Progress tracking
- [ ] Tests

**File:** `packages/api/src/medanki_api/routes/jobs.py`

---

### Chunk 10.5: Download Endpoint
**Time:** 1 hour  
**Dependencies:** 10.4  
**Deliverables:**
- [ ] GET /api/jobs/{job_id}/download
- [ ] File streaming
- [ ] Expiration handling
- [ ] Tests

**File:** `packages/api/src/medanki_api/routes/jobs.py` (extend)

---

### Chunk 10.6: WebSocket Progress
**Time:** 2.5 hours  
**Dependencies:** 10.3  
**Deliverables:**
- [ ] WS /ws/jobs/{job_id}
- [ ] Progress message format
- [ ] Completion/error events
- [ ] Connection management
- [ ] Tests

**File:** `packages/api/src/medanki_api/websocket/progress.py`

---

### Chunk 10.7: Background Processing
**Time:** 2.5 hours  
**Dependencies:** 10.3, Phase 3-8  
**Deliverables:**
- [ ] Async job processor
- [ ] Progress callback integration
- [ ] Error handling and recovery
- [ ] Job cleanup task

**File:** `packages/api/src/medanki_api/workers/processor.py`

---

### Chunk 10.8: Preview Endpoint
**Time:** 1.5 hours  
**Dependencies:** 10.4  
**Deliverables:**
- [ ] GET /api/jobs/{job_id}/preview
- [ ] Card list with pagination
- [ ] Filter by type
- [ ] Tests

**File:** `packages/api/src/medanki_api/routes/preview.py`

---

### Chunk 10.9: API Integration Tests
**Time:** 2 hours  
**Dependencies:** 10.3-10.8  
**Deliverables:**
- [ ] E2E upload → download test
- [ ] WebSocket test
- [ ] Error handling tests

**File:** `tests/integration/test_api.py`

---

## Phase 11: React Frontend

**Goal:** Modern drag-and-drop interface with real-time progress.

### Chunk 11.1: Project Structure & Routing
**Time:** 1.5 hours  
**Dependencies:** 0.3  
**Deliverables:**
- [ ] Route setup (/, /processing/:id, /download/:id)
- [ ] Layout component
- [ ] 404 page
- [ ] Navigation

**Files:**
- `web/src/App.tsx`
- `web/src/pages/`
- `web/src/components/Layout.tsx`

---

### Chunk 11.2: API Client & Types
**Time:** 2 hours  
**Dependencies:** 10.2  
**Deliverables:**
- [ ] Generated types from OpenAPI (or manual)
- [ ] Fetch wrapper with error handling
- [ ] React Query hooks setup
- [ ] WebSocket hook

**Files:**
- `web/src/api/client.ts`
- `web/src/api/types.ts`
- `web/src/hooks/useWebSocket.ts`

---

### Chunk 11.3: Global State Store
**Time:** 1.5 hours  
**Dependencies:** 11.2  
**Deliverables:**
- [ ] Zustand store for app state
- [ ] Current job tracking
- [ ] Settings persistence
- [ ] Toast notifications

**File:** `web/src/stores/appStore.ts`

---

### Chunk 11.4: File Upload Component
**Time:** 3 hours  
**Dependencies:** 11.1  
**Deliverables:**
- [ ] Drag-and-drop zone
- [ ] File type validation
- [ ] Size display
- [ ] Remove file
- [ ] Multiple file support (future)
- [ ] Animations

**Files:**
- `web/src/components/FileUpload.tsx`
- `web/src/components/FilePreview.tsx`

```typescript
// Key structure
interface FileUploadProps {
  onFileSelect: (file: File) => void;
  acceptedTypes: string[];
  maxSizeMB: number;
}

export function FileUpload({ onFileSelect, acceptedTypes, maxSizeMB }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  // Drag handlers, file validation, etc.
}
```

---

### Chunk 11.5: Options Panel Component
**Time:** 1.5 hours  
**Dependencies:** 11.1  
**Deliverables:**
- [ ] Exam type selector (radio buttons)
- [ ] Cards per chunk slider/dropdown
- [ ] Vignettes toggle
- [ ] Settings persistence

**File:** `web/src/components/OptionsPanel.tsx`

---

### Chunk 11.6: Upload Page
**Time:** 2 hours  
**Dependencies:** 11.4, 11.5, 11.2  
**Deliverables:**
- [ ] Compose FileUpload + OptionsPanel
- [ ] Submit handler
- [ ] Loading state
- [ ] Navigation to processing page

**File:** `web/src/pages/UploadPage.tsx`

---

### Chunk 11.7: Progress Components
**Time:** 2.5 hours  
**Dependencies:** 11.2  
**Deliverables:**
- [ ] Progress bar component
- [ ] Step list with status icons
- [ ] Cards counter
- [ ] Animated transitions

**Files:**
- `web/src/components/ProgressBar.tsx`
- `web/src/components/StepList.tsx`
- `web/src/components/ProcessingStats.tsx`

---

### Chunk 11.8: Processing Page
**Time:** 2.5 hours  
**Dependencies:** 11.7, 11.2  
**Deliverables:**
- [ ] WebSocket connection
- [ ] Real-time progress updates
- [ ] Cancel functionality
- [ ] Error handling
- [ ] Auto-redirect on completion

**File:** `web/src/pages/ProcessingPage.tsx`

---

### Chunk 11.9: Card Preview Component
**Time:** 2 hours  
**Dependencies:** 11.2  
**Deliverables:**
- [ ] Card display (cloze rendering)
- [ ] Card list with scroll
- [ ] Tag display
- [ ] Expand/collapse

**Files:**
- `web/src/components/CardPreview.tsx`
- `web/src/components/CardList.tsx`

---

### Chunk 11.10: Download Page
**Time:** 2 hours  
**Dependencies:** 11.9  
**Deliverables:**
- [ ] Success message
- [ ] Download button
- [ ] Card preview section
- [ ] "Generate Another" button
- [ ] Expiration warning

**File:** `web/src/pages/DownloadPage.tsx`

---

### Chunk 11.11: Error Handling & Loading States
**Time:** 1.5 hours  
**Dependencies:** 11.6, 11.8, 11.10  
**Deliverables:**
- [ ] Error boundary
- [ ] Error display component
- [ ] Loading skeletons
- [ ] Retry functionality

**Files:**
- `web/src/components/ErrorBoundary.tsx`
- `web/src/components/LoadingSkeleton.tsx`

---

### Chunk 11.12: Responsive Design & Polish
**Time:** 2 hours  
**Dependencies:** All 11.x  
**Deliverables:**
- [ ] Mobile breakpoints
- [ ] Touch-friendly drop zone
- [ ] Accessibility audit
- [ ] Animation polish

**Files:** Various component updates

---

### Chunk 11.13: Frontend Tests
**Time:** 2.5 hours  
**Dependencies:** All 11.x  
**Deliverables:**
- [ ] Component tests (Vitest + Testing Library)
- [ ] E2E tests (Playwright)
- [ ] Snapshot tests for key components

**Files:** `web/src/__tests__/`, `web/e2e/`

---

## Phase 12: Integration, Testing & Deployment

**Goal:** End-to-end testing, documentation, and deployment.

### Chunk 12.1: Integration Test Suite
**Time:** 3 hours  
**Dependencies:** All previous phases  
**Deliverables:**
- [ ] Full pipeline test: PDF → cards
- [ ] API + Frontend E2E
- [ ] VCR cassettes for LLM calls
- [ ] CI configuration

**Files:** `tests/integration/`, `tests/e2e/`

---

### Chunk 12.2: Property-Based Tests
**Time:** 2 hours  
**Dependencies:** Phase 4, 7  
**Deliverables:**
- [ ] Hypothesis tests for chunking
- [ ] Hypothesis tests for validation
- [ ] Invariant tests

**Files:** `tests/property/`

---

### Chunk 12.3: Documentation
**Time:** 3 hours  
**Dependencies:** All previous phases  
**Deliverables:**
- [ ] README.md with quick start
- [ ] API documentation
- [ ] Architecture overview
- [ ] Deployment guide
- [ ] Contributing guide

**Files:** `docs/`, `README.md`

---

### Chunk 12.4: Docker Production Build
**Time:** 2 hours  
**Dependencies:** 0.4  
**Deliverables:**
- [ ] Multi-stage Dockerfile for API
- [ ] Production nginx config for web
- [ ] docker-compose.prod.yml
- [ ] Health checks

**Files:** `docker/`

---

### Chunk 12.5: GCP Cloud Run Deployment
**Time:** 2.5 hours  
**Dependencies:** 12.4  
**Deliverables:**
- [ ] Cloud Run service configuration
- [ ] Secret management
- [ ] CI/CD deployment workflow
- [ ] Monitoring setup

**Files:** `.github/workflows/deploy.yml`, `docs/deployment.md`

---

### Chunk 12.6: Monitoring & Observability
**Time:** 2 hours  
**Dependencies:** 12.5  
**Deliverables:**
- [ ] Structured logging
- [ ] Error tracking (Sentry optional)
- [ ] Basic metrics
- [ ] Cost tracking dashboard

**Files:** Various

---

### Chunk 12.7: Security Hardening
**Time:** 2 hours  
**Dependencies:** Phase 10, 11  
**Deliverables:**
- [ ] Rate limiting
- [ ] File upload validation
- [ ] CORS lockdown for production
- [ ] Security headers
- [ ] Dependency audit

**Files:** Various

---

### Chunk 12.8: Performance Optimization
**Time:** 2 hours  
**Dependencies:** All previous phases  
**Deliverables:**
- [ ] Embedding batch size tuning
- [ ] Connection pooling
- [ ] Frontend bundle optimization
- [ ] Lazy loading

**Files:** Various

---

## Dependency Graph

```
Phase 0 (Setup)
    │
    ├──→ Phase 1 (Models)
    │        │
    │        └──→ Phase 2 (Services)
    │                 │
    │                 ├──→ Phase 3 (Ingestion)
    │                 │        │
    │                 │        └──→ Phase 4 (Chunking)
    │                 │                 │
    │                 ├──→ Phase 5 (Embeddings) ←──┘
    │                 │        │
    │                 │        └──→ Phase 6 (Classification)
    │                 │                 │
    │                 └──────────────→ Phase 7 (Generation) ←──┘
    │                                    │
    │                                    └──→ Phase 8 (Export)
    │                                             │
    │                                             ├──→ Phase 9 (CLI)
    │                                             │
    └──────────────────────────────────────────→ Phase 10 (API) ←──┘
                                                     │
                                                     └──→ Phase 11 (React)
                                                              │
                                                              └──→ Phase 12 (Deploy)
```

---

## Timeline Estimates

### Aggressive (Full-time, experienced)

| Phase | Chunks | Est. Hours | Days |
|-------|--------|------------|------|
| 0: Setup | 6 | 8 | 1 |
| 1: Models | 6 | 10 | 1.5 |
| 2: Services | 6 | 12 | 1.5 |
| 3: Ingestion | 6 | 12 | 1.5 |
| 4: Chunking | 5 | 10 | 1.5 |
| 5: Embeddings | 4 | 8 | 1 |
| 6: Classification | 4 | 8 | 1 |
| 7: Generation | 7 | 15 | 2 |
| 8: Export | 6 | 12 | 1.5 |
| 9: CLI | 5 | 9 | 1 |
| 10: API | 9 | 17 | 2 |
| 11: React | 13 | 26 | 3.5 |
| 12: Deploy | 8 | 18 | 2.5 |
| **Total** | **85** | **165** | **~22 days** |

### Realistic (Part-time, 3-4 hrs/day)

| Phase | Days |
|-------|------|
| 0: Setup | 3 |
| 1: Models | 4 |
| 2: Services | 5 |
| 3: Ingestion | 5 |
| 4: Chunking | 4 |
| 5: Embeddings | 3 |
| 6: Classification | 3 |
| 7: Generation | 6 |
| 8: Export | 5 |
| 9: CLI | 4 |
| 10: API | 6 |
| 11: React | 10 |
| 12: Deploy | 7 |
| **Total** | **~65 days (~2.5 months)** |

---

## Suggested Sprint Plan

### Sprint 1: Foundation (2 weeks)
- Phase 0: All chunks
- Phase 1: All chunks
- Phase 2: Chunks 2.1, 2.2, 2.4, 2.6

### Sprint 2: Core Pipeline (2 weeks)
- Phase 2: Remaining chunks
- Phase 3: All chunks
- Phase 4: All chunks

### Sprint 3: ML Pipeline (2 weeks)
- Phase 5: All chunks
- Phase 6: All chunks
- Phase 7: Chunks 7.1-7.3

### Sprint 4: Generation & Export (2 weeks)
- Phase 7: Remaining chunks
- Phase 8: All chunks
- Phase 9: All chunks

### Sprint 5: API (1.5 weeks)
- Phase 10: All chunks

### Sprint 6: Frontend (2 weeks)
- Phase 11: Chunks 11.1-11.8

### Sprint 7: Polish & Deploy (2 weeks)
- Phase 11: Remaining chunks
- Phase 12: All chunks

**Total: ~11.5 weeks with buffer = ~3 months**

---

## Quick Reference: Files by Phase

### Phase 0
```
├── pyproject.toml
├── Makefile
├── .env.example
├── docker/docker-compose.yml
├── .github/workflows/ci.yml
├── packages/core/pyproject.toml
├── packages/cli/pyproject.toml
├── packages/api/pyproject.toml
└── web/package.json
```

### Phase 1
```
packages/core/src/medanki/
├── models/
│   ├── __init__.py
│   ├── enums.py
│   ├── document.py
│   ├── chunk.py
│   ├── cards.py
│   └── results.py
├── services/
│   └── protocols.py
└── exceptions.py
```

### Phase 2
```
packages/core/src/medanki/
├── services/
│   ├── config.py
│   ├── taxonomy.py
│   ├── llm.py
│   └── cache.py
└── storage/
    └── sqlite.py
```

### Phase 3
```
packages/core/src/medanki/ingestion/
├── __init__.py
├── pdf.py
├── text.py
├── normalizer.py
└── service.py
```

### Phase 4-6
```
packages/core/src/medanki/processing/
├── __init__.py
├── chunker.py
├── entities.py
├── chunking_service.py
├── embedder.py
├── embedding_service.py
├── classifier.py
└── classification_service.py
```

### Phase 7
```
packages/core/src/medanki/generation/
├── __init__.py
├── cloze.py
├── vignette.py
├── validator.py
├── deduplicator.py
└── service.py
```

### Phase 8
```
packages/core/src/medanki/export/
├── __init__.py
├── tags.py
├── models.py
├── deck.py
├── apkg.py
├── ankiconnect.py
└── service.py
```

### Phase 9
```
packages/cli/src/medanki_cli/
├── __init__.py
├── main.py
└── commands/
    ├── generate.py
    ├── taxonomy.py
    └── config.py
```

### Phase 10
```
packages/api/src/medanki_api/
├── __init__.py
├── main.py
├── routes/
│   ├── upload.py
│   ├── jobs.py
│   └── preview.py
├── websocket/
│   └── progress.py
├── workers/
│   └── processor.py
└── schemas/
    ├── requests.py
    └── responses.py
```

### Phase 11
```
web/src/
├── main.tsx
├── App.tsx
├── api/
│   ├── client.ts
│   └── types.ts
├── stores/
│   └── appStore.ts
├── hooks/
│   └── useWebSocket.ts
├── pages/
│   ├── UploadPage.tsx
│   ├── ProcessingPage.tsx
│   └── DownloadPage.tsx
└── components/
    ├── Layout.tsx
    ├── FileUpload.tsx
    ├── OptionsPanel.tsx
    ├── ProgressBar.tsx
    ├── StepList.tsx
    ├── CardPreview.tsx
    ├── CardList.tsx
    ├── ErrorBoundary.tsx
    └── LoadingSkeleton.tsx
```

---

## Getting Started Checklist

- [ ] Read through all chunks in Phase 0
- [ ] Set up development environment (Python 3.11+, Node 20+, Docker)
- [ ] Get Anthropic API key
- [ ] Clone/create repo
- [ ] Complete Chunk 0.1 → 0.6 in order
- [ ] Verify Weaviate running with `docker-compose up -d`
- [ ] Run `make install` successfully
- [ ] Start Phase 1!

---

*Document version: 1.0 | Last updated: December 2025*
