# MedAnki Documentation

MedAnki is an intelligent flashcard generation system that transforms medical content into Anki-compatible study decks. It leverages AI-powered classification to organize cards by MCAT and USMLE topics.

## Documentation

- [Getting Started](./getting-started.md) - Installation and quick start guide
- [Architecture](./architecture.md) - System design and data flow
- [API Reference](./api-reference.md) - REST API documentation
- [Development](./development.md) - Contributing and development setup
- [Deployment](./deployment.md) - Production deployment guide
- [Taxonomy](./taxonomy.md) - MCAT/USMLE classification system
- [Data Sources](./data-sources.md) - Taxonomy data sources and ingestion

## Overview

MedAnki processes medical documents through a pipeline:

1. **Document Ingestion** - Upload PDFs, markdown, or text files
2. **Chunking** - Split content into optimal-sized pieces using medical-aware tokenization
3. **Classification** - Categorize chunks by MCAT/USMLE topics using hybrid vector search
4. **Card Generation** - Create cloze deletions and clinical vignettes
5. **Export** - Generate Anki-compatible .apkg files

## Quick Links

- [API Endpoints](./api-reference.md#endpoints)
- [Running Tests](./development.md#testing)
- [Docker Deployment](./deployment.md#docker)
