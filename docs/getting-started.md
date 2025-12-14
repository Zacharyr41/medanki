# Getting Started

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for web frontend)

## Installation

### Clone the Repository

```bash
git clone https://github.com/your-org/medanki.git
cd medanki
```

### Install Python Dependencies

```bash
uv sync
```

### Install Web Frontend Dependencies

```bash
cd web
npm install
cd ..
```

## Quick Start

### 1. Start the API Server

```bash
uv run uvicorn medanki_api.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 2. Start the Web Frontend

```bash
cd web
npm run dev
```

The web interface will be available at `http://localhost:5173`.

### 3. Check API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

## First Deck Generation

### Step 1: Upload a Document

Upload your medical content (PDF, markdown, or text) through the web interface or API.

### Step 2: Monitor Processing

The system will:
- Parse and chunk your document
- Classify content by MCAT/USMLE topics
- Generate flashcards (cloze and vignette types)

### Step 3: Preview Cards

Review generated cards in the preview interface:
- Filter by card type (cloze, vignette)
- Filter by topic
- Edit or remove cards as needed

### Step 4: Download Deck

Export your deck as an `.apkg` file and import it into Anki.

## Project Structure

```
medanki/
├── packages/
│   ├── core/           # Core processing logic
│   │   └── src/medanki/
│   │       ├── processing/  # Chunking, classification
│   │       ├── export/      # Anki deck generation
│   │       └── storage/     # SQLite persistence
│   └── api/            # FastAPI REST API
│       └── src/medanki_api/
│           ├── routes/      # API endpoints
│           └── schemas/     # Pydantic models
├── web/                # React frontend
├── tests/              # Test suite
└── docs/               # Documentation
```

## Next Steps

- Read the [Architecture Guide](./architecture.md) to understand the system design
- Explore the [API Reference](./api-reference.md) for endpoint details
- Check [Development](./development.md) for contributing guidelines
