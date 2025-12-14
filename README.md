# MedAnki

Medical flashcard generation from educational content with automatic MCAT/USMLE taxonomy tagging.

## Features

- 📄 Extract content from PDFs, audio lectures, and text files
- 🏷️ Automatic classification against MCAT and USMLE taxonomies
- 🎴 Generate high-quality cloze deletion and clinical vignette cards
- 📦 Export to Anki-compatible .apkg format
- 🌐 Web interface with drag-and-drop upload

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/medanki.git
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

## Development

See [docs/development.md](docs/development.md) for detailed development instructions.

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design documentation.

## License

MIT
