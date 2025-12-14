# MedAnki Dependency Guide
## Complete Reference for All Libraries, APIs, and Secrets

This guide covers every dependency in the MedAnki system, explaining what each does, how to install it, what credentials it needs, and common gotchas.

---

## Table of Contents

1. [Quick Reference: API Keys & Secrets](#quick-reference-api-keys--secrets)
2. [Core Dependencies](#core-dependencies)
3. [Ingestion Layer](#ingestion-layer)
4. [Processing Layer](#processing-layer)
5. [Generation Layer](#generation-layer)
6. [Export Layer](#export-layer)
7. [Infrastructure](#infrastructure)
8. [Development Tools](#development-tools)
9. [Complete Environment Setup](#complete-environment-setup)

---

## Quick Reference: API Keys & Secrets

| Service | Required? | Environment Variable | How to Get | Cost |
|---------|-----------|---------------------|------------|------|
| **Anthropic (Claude)** | ✅ Yes | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | ~$3-15/MTok |
| **OpenAI (optional)** | ❌ No | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | ~$2.50-10/MTok |
| **Weaviate Cloud** | ❌ No* | `WEAVIATE_API_KEY`, `WEAVIATE_URL` | [console.weaviate.cloud](https://console.weaviate.cloud) | Free tier available |
| **Hugging Face** | ❌ No | `HF_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Free |
| **UMLS (NLM)** | ❌ No | `UMLS_API_KEY` | [uts.nlm.nih.gov](https://uts.nlm.nih.gov/uts/signup-login) | Free (requires account) |

*Weaviate can run locally via Docker with no API key needed.

### Minimum Viable Setup

For MVP, you only need **one** API key:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

Everything else can run locally without external services.

---

## Core Dependencies

### 1. Typer (CLI Framework)

**What it does:** Creates the command-line interface with automatic help generation, argument parsing, and rich terminal output.

**Installation:**
```bash
pip install "typer[all]>=0.12.0"
```

**Why Typer over alternatives:**
- Type hints become CLI arguments automatically
- Built-in shell completion
- Integrates with Rich for beautiful output
- Simpler than Click (which it wraps)

**Example usage:**
```python
import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def generate(
    input_path: Path = typer.Argument(..., help="PDF to process"),
    exam: str = typer.Option("usmle", "--exam", "-e"),
):
    """Generate flashcards from medical content."""
    typer.echo(f"Processing {input_path} for {exam}")
```

**No API keys needed.**

---

### 2. Rich (Terminal Formatting)

**What it does:** Provides beautiful terminal output—progress bars, tables, syntax highlighting, markdown rendering.

**Installation:**
```bash
pip install rich>=13.0.0
```

**Included with `typer[all]`** so usually no separate install needed.

**Key features used:**
```python
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

console = Console()

# Progress bar
with Progress() as progress:
    task = progress.add_task("Processing...", total=100)
    progress.update(task, advance=10)

# Pretty printing
console.print("[green]✓[/green] Generated 50 cards")
```

**No API keys needed.**

---

### 3. Pydantic & Pydantic-Settings (Data Validation)

**What it does:** 
- **Pydantic:** Data validation using Python type hints. All our domain models (Document, Chunk, Card) use this.
- **Pydantic-Settings:** Configuration management with environment variable support.

**Installation:**
```bash
pip install pydantic>=2.5.0 pydantic-settings>=2.1.0
```

**Key features:**
```python
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Data model with validation
class ClozeCard(BaseModel):
    text: str = Field(..., min_length=20)
    
    @validator("text")
    def must_have_cloze(cls, v):
        if "{{c1::" not in v:
            raise ValueError("Missing cloze deletion")
        return v

# Settings from environment
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEDANKI_")
    
    anthropic_api_key: str
    weaviate_url: str = "http://localhost:8080"
```

**No API keys needed** (but it reads them from environment).

---

### 4. HTTPX (Async HTTP Client)

**What it does:** Modern async HTTP client for API calls. Better than `requests` for async code.

**Installation:**
```bash
pip install httpx>=0.26.0
```

**Why HTTPX:**
- Native async/await support
- HTTP/2 support
- Connection pooling
- Type hints throughout

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key},
        json={"model": "claude-sonnet-4-5-20250514", ...}
    )
```

**No API keys needed** (client library only).

---

### 5. aiosqlite (Async SQLite)

**What it does:** Async wrapper around SQLite for non-blocking database operations.

**Installation:**
```bash
pip install aiosqlite>=0.19.0
```

**Usage:**
```python
import aiosqlite

async with aiosqlite.connect("medanki.db") as db:
    await db.execute(
        "INSERT INTO documents (id, content) VALUES (?, ?)",
        (doc_id, content)
    )
    await db.commit()
```

**No API keys needed.** SQLite is serverless—just a file.

---

## Ingestion Layer

### 6. Marker (PDF Extraction) ⭐ Primary

**What it does:** Converts PDFs to markdown with excellent accuracy for textbooks, including tables and equations. 25,000+ GitHub stars.

**Installation:**
```bash
pip install marker-pdf
```

**System dependencies (for OCR):**
```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr

# The marker package will download ML models on first run (~2GB)
```

**Usage:**
```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

converter = PdfConverter(artifact_dict=create_model_dict())
result = converter("textbook.pdf")
markdown_text = result.markdown
```

**LLM mode for better tables:**
```python
# Requires OpenAI API key for --use_llm flag
# Set OPENAI_API_KEY environment variable
converter = PdfConverter(config={"use_llm": True})
```

**⚠️ License:** GPL-3.0 — if distributing commercially, consider alternatives.

**API Keys:**
- Basic mode: None
- LLM mode: `OPENAI_API_KEY` (optional enhancement)

---

### 7. Docling (PDF Extraction) — Alternative

**What it does:** IBM's PDF extraction library with excellent table handling. MIT licensed (commercial-friendly).

**Installation:**
```bash
pip install docling
```

**Usage:**
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")
markdown = result.document.export_to_markdown()
```

**No API keys needed.**

---

### 8. PyMuPDF / PyMuPDF4LLM (Fast PDF Extraction)

**What it does:** Extremely fast PDF text extraction (~50 pages/second). Good for bulk processing where quality can be slightly lower.

**Installation:**
```bash
pip install pymupdf pymupdf4llm
```

**Usage:**
```python
import pymupdf4llm

# Get markdown with page-level chunking
md_chunks = pymupdf4llm.to_markdown("textbook.pdf", page_chunks=True)
# Returns: [{"text": "...", "metadata": {"page": 1}}, ...]
```

**No API keys needed.**

---

### 9. OpenAI Whisper (Audio Transcription)

**What it does:** Transcribes audio/video lectures to text with word-level timestamps.

**Installation:**
```bash
# Local model (free, runs on your machine)
pip install openai-whisper

# Or via OpenAI API (paid, faster)
pip install openai
```

**System dependencies:**
```bash
# FFmpeg required for audio processing
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

**Local usage (no API key):**
```python
import whisper

model = whisper.load_model("large-v3")  # Downloads ~3GB model
result = model.transcribe("lecture.mp3", word_timestamps=True)
```

**API usage:**
```python
from openai import OpenAI

client = OpenAI()  # Uses OPENAI_API_KEY
with open("lecture.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )
```

**API Keys:**
- Local: None (but needs ~6GB VRAM for large-v3)
- API: `OPENAI_API_KEY` — $0.006/minute of audio

---

## Processing Layer

### 10. scispaCy (Medical NLP) ⭐ Critical

**What it does:** spaCy models trained on biomedical text. Provides:
- Medical named entity recognition (NER)
- UMLS concept linking
- Abbreviation detection

**Installation:**
```bash
pip install scispacy>=0.5.4

# Download medical NER model (~400MB)
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Optional: UMLS linker for concept normalization
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz
```

**Usage:**
```python
import spacy

nlp = spacy.load("en_core_sci_lg")

# Add UMLS linker (requires UMLS license for full functionality)
nlp.add_pipe("scispacy_linker", config={
    "resolve_abbreviations": True,
    "linker_name": "umls"
})

doc = nlp("Patient has CHF and takes metoprolol")
for ent in doc.ents:
    print(f"{ent.text}: {ent.label_}")
# Output: CHF: DISEASE, metoprolol: DRUG
```

**API Keys:**
- Basic NER: None
- Full UMLS linking: `UMLS_API_KEY` (free but requires NLM account)

**Getting UMLS access:**
1. Go to [uts.nlm.nih.gov/uts/signup-login](https://uts.nlm.nih.gov/uts/signup-login)
2. Create account (requires identity verification)
3. Accept UMLS license agreement
4. Generate API key in profile settings

---

### 11. sentence-transformers (Embeddings)

**What it does:** Generates dense vector embeddings from text for semantic similarity search.

**Installation:**
```bash
pip install sentence-transformers>=2.3.0
```

**Usage with PubMedBERT:**
```python
from sentence_transformers import SentenceTransformer

# Load medical-domain model
model = SentenceTransformer("neuml/pubmedbert-base-embeddings")

# Generate embeddings
embeddings = model.encode([
    "myocardial infarction treatment",
    "heart attack therapy"
])
# Returns: numpy array shape (2, 768)
```

**Available medical models:**

| Model | Dimensions | Best For |
|-------|------------|----------|
| `neuml/pubmedbert-base-embeddings` | 768 | General medical |
| `pritamdeka/S-PubMedBert-MS-MARCO` | 768 | Information retrieval |
| `NeuML/pubmedbert-base-embeddings-matryoshka` | 64-768 | Flexible storage |

**Hardware requirements:**
- CPU: Works but slow (~0.5s per batch)
- GPU: Much faster (~0.05s per batch)
- Model download: ~400MB

**No API keys needed.** Runs entirely locally.

---

### 12. Weaviate (Vector Database) ⭐ Critical

**What it does:** Vector database with native hybrid search (BM25 + semantic). Critical for matching abbreviations like "CHF" that pure semantic search misses.

**Installation:**
```bash
pip install weaviate-client>=4.4.0
```

**Option A: Local Docker (Recommended for development)**
```bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -p 50051:50051 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
  -v weaviate_data:/var/lib/weaviate \
  semitechnologies/weaviate:1.24.1
```

**Usage:**
```python
import weaviate

# Local connection (no auth)
client = weaviate.connect_to_local()

# Or cloud connection
client = weaviate.connect_to_weaviate_cloud(
    cluster_url="https://your-cluster.weaviate.network",
    auth_credentials=weaviate.auth.AuthApiKey("your-api-key")
)

# Hybrid search
result = client.query.get("MedicalChunk", ["text", "topic"]).with_hybrid(
    query="heart failure treatment",
    alpha=0.5  # Balance BM25 and vector
).with_limit(10).do()
```

**Option B: Weaviate Cloud**
1. Go to [console.weaviate.cloud](https://console.weaviate.cloud)
2. Create free sandbox cluster
3. Get URL and API key from cluster details

**API Keys:**
- Local Docker: None
- Cloud: `WEAVIATE_URL` + `WEAVIATE_API_KEY`

**Cost:**
- Local: Free
- Cloud Sandbox: Free (limited resources)
- Cloud Production: ~$25/month minimum

---

### 13. ChromaDB (Vector Database) — Alternative

**What it does:** Simpler vector database, good for prototyping. No hybrid search (semantic only).

**Installation:**
```bash
pip install chromadb
```

**Usage:**
```python
import chromadb

client = chromadb.Client()  # In-memory
# Or persistent:
client = chromadb.PersistentClient(path="./chroma_db")

collection = client.create_collection("medical_chunks")
collection.add(
    documents=["heart failure symptoms"],
    embeddings=[[0.1, 0.2, ...]],
    ids=["doc1"]
)
```

**No API keys needed.** Fully local.

---

## Generation Layer

### 14. Anthropic SDK (Claude API) ⭐ Critical

**What it does:** Official Python client for Claude API. Used for flashcard generation and validation.

**Installation:**
```bash
pip install anthropic>=0.18.0
```

**Usage:**
```python
from anthropic import Anthropic

client = Anthropic()  # Reads ANTHROPIC_API_KEY from env

response = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": "Generate 3 cloze flashcards from: ..."
    }]
)
```

**Getting API Key:**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / log in
3. Go to API Keys section
4. Create new key

**Pricing (as of late 2024):**

| Model | Input | Output |
|-------|-------|--------|
| Claude Sonnet 4 | $3/MTok | $15/MTok |
| Claude Opus 4 | $15/MTok | $75/MTok |
| Claude Haiku | $0.25/MTok | $1.25/MTok |

**Estimated cost per lecture:**
- ~5,000 tokens input (chunked lecture)
- ~2,000 tokens output (generated cards)
- **~$0.02-0.05 per lecture** with Sonnet

---

### 15. Instructor (Structured LLM Output)

**What it does:** Forces LLM outputs to match Pydantic schemas. Handles retries on validation failure.

**Installation:**
```bash
pip install instructor>=1.0.0
```

**Usage:**
```python
import instructor
from pydantic import BaseModel
from anthropic import Anthropic

class ClozeCard(BaseModel):
    text: str
    extra: str

client = instructor.from_anthropic(Anthropic())

cards = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    response_model=list[ClozeCard],  # Enforces schema!
    max_tokens=1024,
    messages=[{"role": "user", "content": "Generate cards..."}],
    max_retries=3  # Auto-retry on validation failure
)
```

**No additional API keys** — uses whatever LLM client you wrap.

---

### 16. LiteLLM (Multi-Provider Abstraction) — Optional

**What it does:** Unified interface to 100+ LLM providers. Useful if you want to switch between Claude/GPT-4/local models.

**Installation:**
```bash
pip install litellm
```

**Usage:**
```python
from litellm import completion

# Same interface for any provider
response = completion(
    model="anthropic/claude-sonnet-4-5-20250514",  # or "gpt-4", "ollama/llama2"
    messages=[{"role": "user", "content": "Hello"}]
)
```

**API Keys:** Depends on which provider you use.

---

## Export Layer

### 17. genanki (Anki Deck Generation) ⭐ Critical

**What it does:** Creates `.apkg` files (Anki deck packages) programmatically without needing Anki installed.

**Installation:**
```bash
pip install genanki>=0.13.0
```

**Usage:**
```python
import genanki

# Define model (card template)
model = genanki.Model(
    1607392319,  # Unique, stable ID
    'Medical Cloze',
    model_type=genanki.Model.CLOZE,
    fields=[{'name': 'Text'}, {'name': 'Extra'}],
    templates=[{
        'name': 'Cloze',
        'qfmt': '{{cloze:Text}}',
        'afmt': '{{cloze:Text}}<hr>{{Extra}}'
    }]
)

# Create deck
deck = genanki.Deck(2059400110, 'Medical::Cardiology')

# Add note
note = genanki.Note(
    model=model,
    fields=['The {{c1::heart}} has four chambers', 'Basic anatomy'],
    tags=['cardiology', 'anatomy']
)
deck.add_note(note)

# Export
package = genanki.Package(deck)
package.write_to_file('output.apkg')
```

**Critical details:**
- Model/Deck IDs must be **stable** across runs (hardcode them!)
- Use content-based GUIDs for notes to handle updates properly
- Cloze syntax: `{{c1::answer}}` with 1-indexed numbers

**No API keys needed.** Pure Python library.

---

### 18. AnkiConnect (Live Sync) — Optional

**What it does:** REST API to communicate with running Anki instance. Allows real-time card creation without file import.

**Installation:**
1. Open Anki
2. Tools → Add-ons → Get Add-ons
3. Enter code: `2055492159`
4. Restart Anki

**Usage:**
```python
import requests

def anki_invoke(action, params=None):
    return requests.post('http://localhost:8765', json={
        'action': action,
        'version': 6,
        'params': params or {}
    }).json()

# Add card directly to Anki
anki_invoke('addNote', {
    'note': {
        'deckName': 'Medical',
        'modelName': 'Basic',
        'fields': {'Front': 'Question', 'Back': 'Answer'},
        'tags': ['test']
    }
})
```

**Requirements:**
- Anki must be running
- Only works on localhost

**No API keys needed.**

---

## Infrastructure

### 19. uv (Package Manager)

**What it does:** Next-generation Python package manager. 10-100x faster than pip/poetry.

**Installation:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

**Usage:**
```bash
# Create project
uv init medanki
cd medanki

# Add dependencies
uv add anthropic genanki typer

# Run scripts
uv run python main.py

# Sync from pyproject.toml
uv sync
```

**No API keys needed.**

---

### 20. Docker (Containerization)

**What it does:** Runs Weaviate and other services in isolated containers.

**Installation:** [docs.docker.com/get-docker](https://docs.docker.com/get-docker/)

**docker-compose.yml for MedAnki:**
```yaml
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
    volumes:
      - weaviate_data:/var/lib/weaviate

volumes:
  weaviate_data:
```

**No API keys needed** for local Docker.

---

## Development Tools

### 21. pytest (Testing)

```bash
pip install pytest pytest-asyncio pytest-vcr hypothesis
```

### 22. Ruff (Linting/Formatting)

```bash
pip install ruff
```

### 23. mypy (Type Checking)

```bash
pip install mypy
```

---

## Complete Environment Setup

### Minimal .env File

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Optional - only if using cloud Weaviate
# WEAVIATE_URL=https://your-cluster.weaviate.network
# WEAVIATE_API_KEY=xxxxx

# Optional - only if using Marker LLM mode or Whisper API
# OPENAI_API_KEY=sk-xxxxx

# Optional - only if using full UMLS linking
# UMLS_API_KEY=xxxxx

# Optional - for downloading some HuggingFace models
# HF_TOKEN=hf_xxxxx
```

### Complete pyproject.toml

```toml
[project]
name = "medanki"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Core
    "typer[all]>=0.12.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "httpx>=0.26.0",
    "aiosqlite>=0.19.0",
    
    # Ingestion
    "marker-pdf>=0.3.0",
    "pymupdf>=1.23.0",
    
    # Processing
    "scispacy>=0.5.4",
    "spacy>=3.7.0",
    "sentence-transformers>=2.3.0",
    "weaviate-client>=4.4.0",
    
    # Generation
    "anthropic>=0.18.0",
    "instructor>=1.0.0",
    
    # Export
    "genanki>=0.13.0",
]

[project.optional-dependencies]
audio = ["openai-whisper"]
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
```

### Installation Commands

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone/create project
git clone <repo> && cd medanki
# or: uv init medanki && cd medanki

# 3. Install dependencies
uv sync

# 4. Download scispaCy model
uv run pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# 5. Start Weaviate
docker-compose up -d

# 6. Set API key
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# 7. Run
uv run medanki generate lecture.pdf --exam usmle-step1
```

---

## Cost Estimates

### Per-Lecture Processing

| Component | Cost |
|-----------|------|
| PDF Extraction | Free (local) |
| Embedding | Free (local) |
| Classification | Free (local) |
| Card Generation (Claude) | ~$0.02-0.05 |
| Validation (Claude) | ~$0.01-0.02 |
| Export | Free (local) |
| **Total** | **~$0.03-0.07 per lecture** |

### Monthly Infrastructure

| Service | Local | Cloud |
|---------|-------|-------|
| Weaviate | Free (Docker) | $25+/month |
| Claude API | Pay-per-use | Pay-per-use |
| Compute | Your machine | $10-50/month (GCP) |

### Typical Usage (50 lectures/month)

- Claude API: ~$2.50-3.50
- Infrastructure: $0 (local) or $35+ (cloud)
- **Total: $3-40/month** depending on setup

---

## Troubleshooting Common Issues

### "CUDA out of memory" with embeddings
```bash
# Force CPU
export CUDA_VISIBLE_DEVICES=""
```

### Marker fails on scanned PDFs
```bash
# Install Tesseract OCR
brew install tesseract  # macOS
sudo apt-get install tesseract-ocr  # Ubuntu
```

### scispaCy model not found
```bash
# Re-download the model
python -m spacy download en_core_sci_lg
```

### Weaviate connection refused
```bash
# Check if running
docker ps | grep weaviate

# Restart if needed
docker-compose restart weaviate
```

---

*Document version: 1.0 | Last updated: December 2025*
