# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-14

### Added

- **TaxonomyServiceV2** with SQLite backend and closure table hierarchy
  - Full ancestor/descendant traversal via closure table
  - Keyword search with exam filtering
  - Semantic search support via vector store protocol
  - AnKing-style tag generation
  - Cross-classification support for USMLE systems/disciplines

- **ClassificationServiceV2** for taxonomy-based content classification
  - Hybrid search combining semantic and keyword matching
  - Configurable thresholds for classification precision

- **Taxonomy Database Pipeline**
  - `make taxonomy-build` - Build SQLite database from JSON taxonomies
  - `make taxonomy-enrich` - Enrich with external sources
  - `make taxonomy-stats` - Display database statistics

- **Taxonomy API Endpoints**
  - `GET /taxonomy/exams` - List available exams
  - `GET /taxonomy/{exam}/root` - Get root nodes for an exam
  - `GET /taxonomy/nodes/{node_id}` - Get node by ID
  - `GET /taxonomy/nodes/{node_id}/children` - Get child nodes
  - `GET /taxonomy/search` - Search nodes by keyword

- **External Data Integrations**
  - MeSH API client for medical vocabulary enrichment
  - Hugging Face dataset ingestion pipeline
  - AnKing deck parser for existing flashcard analysis

### Changed

- Database schema now includes tables for:
  - `taxonomy_closure` - Closure table for hierarchy traversal
  - `keywords` - Search keywords per node
  - `cross_classifications` - USMLE system/discipline mappings
  - `mesh_concepts` and `mesh_mappings` - MeSH vocabulary
  - `anking_tags` - AnKing tag mappings
  - `resources` and `resource_mappings` - External resource links

### Fixed

- Mypy type errors in taxonomy_repository.py
- Ruff linting errors across codebase
- WebSocket test patterns
- Test import paths

## [0.1.0] - 2024-12-01

### Added

- Initial release
- Core document processing pipeline
- PDF and text ingestion
- Cloze and vignette card generation
- MCAT and USMLE taxonomy support
- Anki deck export (.apkg)
- FastAPI backend with WebSocket progress
- React frontend with card preview
