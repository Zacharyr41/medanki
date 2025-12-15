# Data Sources

MedAnki's taxonomy system integrates multiple data sources to provide comprehensive medical topic classification.

## Static Taxonomy Files

### mcat.json

Location: `data/taxonomies/mcat.json`

Contains the MCAT content outline structure:
- 10 Foundational Concepts (FC1-FC10)
- Content Categories (1A, 1B, 2A, etc.)
- Keywords for each category

```json
{
  "exam": "MCAT",
  "version": "2024",
  "foundational_concepts": [
    {
      "id": "FC1",
      "title": "Biomolecules have unique properties...",
      "categories": [
        {
          "id": "1A",
          "title": "Structure and function of proteins...",
          "keywords": ["amino acids", "protein", "enzymes"]
        }
      ]
    }
  ]
}
```

### usmle_step1.json

Location: `data/taxonomies/usmle_step1.json`

Contains the USMLE Step 1 content outline:
- 10 Organ Systems (General Principles, Cardiovascular, etc.)
- Topics within each system
- Keywords for classification

```json
{
  "exam": "USMLE_STEP1",
  "version": "2024",
  "systems": [
    {
      "id": "SYS3",
      "title": "Cardiovascular System",
      "topics": [
        {
          "id": "SYS3A",
          "title": "Cardiac Anatomy and Physiology",
          "keywords": ["heart anatomy", "cardiac cycle", "ECG"]
        }
      ]
    }
  ]
}
```

## External API Sources

### MeSH (Medical Subject Headings)

The MeSH API client (`scripts/ingest/mesh_api.py`) retrieves medical vocabulary from NIH:

```bash
# Search MeSH descriptors
python scripts/ingest/mesh_api.py search "hypertension"

# Get synonyms for a term
python scripts/ingest/mesh_api.py get-synonyms "Myocardial Infarction"

# Build vocabulary file from MeSH categories
python scripts/ingest/mesh_api.py build-vocab --categories "C,D" --output data/mesh_vocab.json
```

MeSH categories used:
- **C** - Diseases
- **D** - Chemicals and Drugs
- **A** - Anatomy
- **G** - Phenomena and Processes

### Hugging Face Datasets

The Hugging Face ingestion pipeline (`scripts/ingest/huggingface.py`) extracts topics from medical Q&A datasets.

#### MedMCQA Dataset

Source: `openlifescienceai/medmcqa`
- 193,000+ medical MCQ questions
- 21 subjects (Anatomy, Physiology, Pharmacology, etc.)
- 2,400+ unique topics

```bash
# Extract topics from MedMCQA
python scripts/ingest/huggingface.py extract-topics -o data/hf/medmcqa_topics.json
```

#### MedQA Dataset

Source: `GBaker/MedQA-USMLE-4-options`
- 11,500+ USMLE-style questions
- Step 1, Step 2, Step 3 coverage

#### Medical Flashcards

Source: `medalpaca/medical_meadow_medical_flashcards`
- 33,000+ medical Q&A pairs

```bash
# Download all datasets
python scripts/ingest/huggingface.py download-all -o data/hf/
```

## AnKing Deck Integration

The AnKing parser (`scripts/ingest/anking_export.py`) extracts tag hierarchies from AnKing deck exports:

```bash
# Extract tags from AnKing deck
python scripts/ingest/anking_export.py extract-tags data/source/anking/AnKing-v11 -o data/anking_tags.json

# List resources found in deck
python scripts/ingest/anking_export.py list-resources data/source/anking/AnKing-v11
```

### Supported Resources
- First Aid
- Pathoma
- Boards & Beyond
- Sketchy (Micro, Pharm, Path)
- Costanzo Physiology
- UWorld

## Ingestion Pipeline

### Building the Taxonomy Database

```bash
# 1. Extract MedMCQA topics
python scripts/ingest/huggingface.py extract-topics

# 2. Build MeSH vocabulary
python scripts/ingest/mesh_api.py build-vocab

# 3. Extract AnKing tags (requires deck export)
python scripts/ingest/anking_export.py extract-tags

# 4. Enrich taxonomy with keywords
python scripts/ingest/huggingface.py enrich-taxonomy \
    --taxonomy data/taxonomies/usmle_step1.json \
    --topics data/hf/medmcqa_topics.json
```

### Data Flow

```
Static JSON Files
       │
       ▼
┌─────────────────┐
│  TaxonomyRepo   │◄──── MeSH API
│    (SQLite)     │◄──── Hugging Face
└────────┬────────┘◄──── AnKing Export
         │
         ▼
┌─────────────────┐
│ TaxonomyService │
│    (V2)         │
└────────┬────────┘
         │
         ▼
   Classification
      Service
```

## Data Freshness

| Source | Update Frequency | Notes |
|--------|-----------------|-------|
| mcat.json | Annual | Based on AAMC content outline |
| usmle_step1.json | Annual | Based on NBME content outline |
| MeSH | Cached | 15-minute cache, refresh as needed |
| MedMCQA | Static | Dataset snapshot |
| AnKing | Per-release | Extract from new deck versions |
