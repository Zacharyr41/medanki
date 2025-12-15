# MedAnki

Transform medical content into intelligent Anki flashcards with AI-powered classification.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](LICENSE)

## Features

- **Smart Document Processing** - Upload PDFs, markdown, or text files
- **Medical-Aware Chunking** - Preserves lab values, drug doses, and anatomical terms
- **AI Classification** - Automatic MCAT/USMLE topic tagging using hybrid vector search
- **Multiple Card Types** - Cloze deletions, clinical vignettes, and basic Q&A
- **Anki Export** - Generate `.apkg` files ready for import
- **Preview & Edit** - Review cards before export with filtering options
- **REST API** - Integrate with your own applications

## Taxonomy

MedAnki uses a hierarchical taxonomy system backed by SQLite with closure tables for efficient hierarchy queries.

### Supported Exams
- **MCAT** - 10 Foundational Concepts with content categories (1A-10A)
- **USMLE Step 1** - 10 Organ Systems with discipline cross-classification

### Data Sources
- Official AAMC/NBME content outlines
- MeSH (Medical Subject Headings) vocabulary enrichment
- Hugging Face medical datasets (MedMCQA, MedQA)
- AnKing deck tag structure

See [docs/taxonomy.md](docs/taxonomy.md) for detailed taxonomy documentation.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for web frontend)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/medanki.git
cd medanki

# Run setup
chmod +x setup.sh
./setup.sh

# Start Docker services (Weaviate)
make docker-up

# Install dependencies
make install-dev

# Run tests
make test
```

### Verify Installation

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

## Usage

### Web Interface

1. Navigate to `http://localhost:5173`
2. Upload your medical document
3. Wait for processing to complete
4. Preview and edit generated cards
5. Download your Anki deck

### API

```bash
# Get card preview for a job
curl "http://localhost:8000/api/jobs/{job_id}/preview?limit=10"

# Download deck
curl -O "http://localhost:8000/api/jobs/{job_id}/download"

# Get job statistics
curl "http://localhost:8000/api/jobs/{job_id}/stats"
```

## Development

See [docs/development.md](docs/development.md) for detailed development instructions.

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design documentation.

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first deck |
| [Architecture](docs/architecture.md) | System design and data flow |
| [API Reference](docs/api-reference.md) | REST endpoint documentation |
| [Development](docs/development.md) | Contributing and setup |
| [Deployment](docs/deployment.md) | Docker and Cloud Run |
| [Taxonomy](docs/taxonomy.md) | MCAT/USMLE classification |

## Project Structure

```
medanki/
├── packages/
│   ├── core/           # Processing, export, storage
│   └── api/            # FastAPI REST API
├── web/                # React frontend
├── tests/              # Test suite
└── docs/               # Documentation
```

## Running Tests

```bash
uv run pytest
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING](docs/development.md#contributing-guidelines) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Write tests
4. Submit a pull request

## Acknowledgments

- [Anki](https://apps.ankiweb.net/) - Spaced repetition software
- [genanki](https://github.com/kerrickstaley/genanki) - Anki deck generation
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [tiktoken](https://github.com/openai/tiktoken) - Token counting
