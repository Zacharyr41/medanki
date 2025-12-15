# MedAnki Project Context

## Project Overview
MedAnki converts medical education materials (PDFs, audio lectures, transcripts) into high-quality Anki flashcards automatically tagged against MCAT and USMLE taxonomies. The system solves the "joining problem" of semantically matching lecture content to standardized exam topics.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│  ┌─────────────────┐              ┌─────────────────────────┐   │
│  │   CLI (Typer)   │              │  Web (React + FastAPI)  │   │
│  └─────────────────┘              └─────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                        MedAnki Core                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Ingestion │→ │Processing│→ │Generation│→ │  Export  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  Shared: Config | Taxonomy | LLM Client | Cache                 │
├─────────────────────────────────────────────────────────────────┤
│  Data: Weaviate (vectors) | SQLite (metadata) | Filesystem      │
└─────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
medanki/
├── packages/
│   ├── core/src/medanki/          # Core library
│   │   ├── models/                # Domain models (Document, Chunk, Card)
│   │   ├── ingestion/             # PDF, audio, text extraction
│   │   ├── processing/            # Chunking, embedding, classification
│   │   ├── generation/            # Card generation, validation
│   │   ├── export/                # genanki, AnkiConnect
│   │   ├── services/              # Config, taxonomy, LLM, cache
│   │   └── storage/               # SQLite, Weaviate adapters
│   ├── cli/src/medanki_cli/       # CLI application
│   └── api/src/medanki_api/       # FastAPI backend
├── web/src/                       # React frontend
├── data/taxonomies/               # MCAT/USMLE JSON schemas
├── tests/                         # Test suites
└── docker/                        # Docker configurations
```

## Tech Stack

### Backend (Python 3.11+)
- **Package Manager:** uv
- **Web Framework:** FastAPI with WebSocket
- **Validation:** Pydantic v2
- **Database:** aiosqlite (async SQLite)
- **Vector Store:** Weaviate (hybrid search)
- **Embeddings:** PubMedBERT via sentence-transformers
- **NLP:** scispaCy for medical NER
- **LLM:** Claude Sonnet 4 via anthropic SDK + instructor
- **PDF:** Marker (primary), PyMuPDF4LLM (fallback)
- **Anki:** genanki for .apkg generation

### Frontend (TypeScript)
- **Framework:** React 18 with Vite
- **Styling:** TailwindCSS
- **Data Fetching:** React Query (TanStack Query)
- **State:** Zustand
- **Routing:** React Router v6

## Key Commands

```bash
# Install all dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/ -v
uv run pytest tests/unit -v --tb=short  # Quick unit tests

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy packages/

# Start development servers
uv run uvicorn medanki_api.main:app --reload --port 8000  # API
cd web && npm run dev  # Frontend (port 5173)

# Docker services
docker compose -f docker/docker-compose.yml up -d  # Weaviate on :8080
```

## Code Standards

### Python
- Type hints everywhere (strict mode)
- Async/await for all I/O operations
- Pydantic models for all data structures
- Protocol classes for dependency injection
- Google-style docstrings
- 100-character line limit (ruff)
- Tests alongside implementation

### TypeScript/React
- Functional components only (no classes)
- TypeScript strict mode - no `any`
- Custom hooks for reusable logic
- TailwindCSS utilities (no inline styles)
- React Query for all API calls

## Important Patterns

### Python Service Pattern
```python
from medanki.services.protocols import IChunkingService

class ChunkingService(IChunkingService):
    """Service for chunking documents with medical term preservation."""
    
    def __init__(self, config: Settings, nlp_pipeline: spacy.Language):
        self._config = config
        self._nlp = nlp_pipeline
    
    async def chunk_document(self, document: Document) -> list[Chunk]:
        """Chunk a document respecting medical terminology."""
        # Implementation
```

### React Component Pattern
```tsx
interface FileUploadProps {
  onFileSelect: (file: File) => void;
  acceptedTypes: string[];
  maxSizeMB: number;
}

export function FileUpload({ onFileSelect, acceptedTypes, maxSizeMB }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const handleDrop = useCallback((e: DragEvent) => {
    // Handler logic
  }, [onFileSelect]);
  
  if (!selectedFile) {
    return <DropZone onDrop={handleDrop} isDragging={isDragging} />;
  }
  
  return <FilePreview file={selectedFile} onRemove={() => setSelectedFile(null)} />;
}
```

### Cloze Card Validation
```python
import re

CLOZE_PATTERN = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")

def validate_cloze(text: str) -> bool:
    """Validate cloze syntax: {{c1::answer}}"""
    matches = CLOZE_PATTERN.findall(text)
    if not matches:
        return False
    for idx, answer in matches:
        if len(answer.split()) > 4:  # Max 4 words
            return False
    return True
```

## Key Constants

```python
# Model IDs (NEVER CHANGE - breaks Anki sync)
CLOZE_MODEL_ID = 1607392319001
VIGNETTE_MODEL_ID = 1607392319003

# Processing
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 75  # tokens
EMBEDDING_DIM = 768  # PubMedBERT

# Classification
BASE_THRESHOLD = 0.65
RELATIVE_THRESHOLD = 0.80
HYBRID_ALPHA = 0.5  # Balance BM25 and semantic
```

## Current Sprint Focus
<!-- Update this section as you progress -->
- **Phase:** [Current phase number]
- **Chunk:** [Current chunk]
- **Focus:** [What you're working on]

## Known Issues / TODOs
<!-- Track ongoing issues -->
- [ ] 

## Testing Notes

### Python Tests
```bash
# Run specific test file
uv run pytest tests/unit/models/test_cards.py -v

# Run with coverage
uv run pytest tests/ --cov=medanki --cov-report=html

# Use VCR for LLM tests
@pytest.mark.vcr()
async def test_generation():
    ...
```

### React Tests
```bash
cd web
npm test              # Watch mode
npm test -- --run     # Single run
npm run test:e2e      # Playwright E2E
```

## Environment Variables

**Required:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

**Optional:**
```bash
WEAVIATE_URL=http://localhost:8080    # Default
MEDANKI_DEBUG=false                   # Enable debug logging
MEDANKI_ENABLE_VIGNETTES=true         # Generate vignettes
MEDANKI_MAX_CARDS_PER_CHUNK=5         # Card limit
```

## Reference Files

When implementing new features, reference these files:
- **Models:** `packages/core/src/medanki/models/`
- **Protocols:** `packages/core/src/medanki/services/protocols.py`
- **Config:** `packages/core/src/medanki/config.py`
- **Test Spec:** `medanki_test_specification.py`
- **Taxonomies:** `data/taxonomies/*.json`

## Agents Available

Use these agent prefixes for specialized help:
- `@python-backend` - Core library, FastAPI, services
- `@react-frontend` - React components, pages, hooks
- `@test-engineer` - Testing (Python + React)
- `@medical-nlp` - Taxonomy, NER, classification
- `@devops` - Docker, CI/CD, deployment
- `@anki-specialist` - Cards, decks, genanki

## Common Gotchas

1. **Weaviate must be running** for integration tests
2. **scispaCy model** needs separate download: `pip install en_core_sci_lg`
3. **Cloze syntax** is `{{c1::answer}}` (1-indexed)
4. **Model IDs** must never change or Anki import breaks
5. **Hybrid search alpha** - lower values favor keyword (abbreviations)
6. **Run ruff** before committing: `uv run ruff check --fix .`
