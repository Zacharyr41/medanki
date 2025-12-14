# MedAnki Comprehensive Taxonomy Implementation Plan

## Executive Summary

This document provides a detailed implementation plan for building a comprehensive taxonomy system for the MedAnki project. Based on analysis of the existing codebase and the Complete Medical Education Taxonomy research, this plan extends the current `TaxonomyService` and data files to support:

- **Complete MCAT taxonomy**: 10 Foundational Concepts, 30+ Content Categories, full topic/subtopic coverage
- **Complete USMLE Step 1 taxonomy**: 18 organ systems, 10 disciplines, resource integration (First Aid, Pathoma, Sketchy, Boards & Beyond, AnKing)
- **USMLE Step 2 CK taxonomy**: Clinical rotations, chief complaints, discipline breakdown
- **External data integration**: Hugging Face datasets, MeSH vocabulary, AnKing tag exports
- **Database architecture**: SQLite for metadata/relationships, Weaviate for semantic search

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Target Architecture](#2-target-architecture)
3. [Database Schema Design](#3-database-schema-design)
4. [Comprehensive JSON Taxonomy Files](#4-comprehensive-json-taxonomy-files)
5. [Data Ingestion Scripts](#5-data-ingestion-scripts)
6. [Enhanced TaxonomyService](#6-enhanced-taxonomyservice)
7. [External Data Source Integration](#7-external-data-source-integration)
8. [Implementation Phases](#8-implementation-phases)
9. [Testing Strategy](#9-testing-strategy)

---

## 1. Current State Analysis

### Existing Files
```
medanki/
├── data/taxonomies/
│   ├── mcat.json           # Basic: 10 FCs, ~20 categories, minimal keywords
│   └── usmle_step1.json    # Basic: 10 systems, ~20 topics
├── packages/core/src/medanki/
│   ├── services/
│   │   └── taxonomy.py     # TaxonomyService with basic CRUD
│   ├── processing/
│   │   └── classifier.py   # ClassificationService using hybrid search
│   └── storage/
│       ├── sqlite.py       # SQLite for jobs/metadata
│       └── weaviate.py     # Vector store for semantic search
```

### Current Limitations

1. **Incomplete Taxonomy Coverage**
   - MCAT: Missing many subtopics, incomplete keyword lists, no researcher names
   - USMLE: Missing disciplines dimension, no resource mapping (First Aid chapters, Pathoma chapters)

2. **Flat Structure**
   - Current JSON schema only supports 2 levels (FC→Category or System→Topic)
   - USMLE requires 2D classification (System × Discipline)
   - No support for resource-level tagging (Sketchy videos, B&B chapters)

3. **No External Data Integration**
   - No scripts to pull from Hugging Face datasets
   - No MeSH/UMLS vocabulary integration
   - No AnKing tag import capability

---

## 2. Target Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MedAnki Taxonomy System                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Data Sources Layer                                  │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │ │
│  │  │   AAMC     │ │   NBME     │ │ Hugging    │ │   AnKing   │ │   MeSH   │ │ │
│  │  │  Outline   │ │  Outline   │ │   Face     │ │  Export    │ │   API    │ │ │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────┬─────┘ │ │
│  └────────┼──────────────┼──────────────┼──────────────┼─────────────┼───────┘ │
│           │              │              │              │             │          │
│           ▼              ▼              ▼              ▼             ▼          │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                       Ingestion Scripts Layer                               │ │
│  │  ingest_aamc.py  ingest_nbme.py  ingest_hf.py  ingest_anking.py  mesh.py   │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                          │
│                                      ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                           Storage Layer                                     │ │
│  │  ┌───────────────────────────┐    ┌───────────────────────────────────┐    │ │
│  │  │       SQLite Database     │    │        Weaviate Vector DB         │    │ │
│  │  │  ┌─────────────────────┐  │    │  ┌─────────────────────────────┐  │    │ │
│  │  │  │ exams               │  │    │  │ TaxonomyTopic Collection    │  │    │ │
│  │  │  │ taxonomy_nodes      │  │    │  │ - topic_id (ref)            │  │    │ │
│  │  │  │ taxonomy_edges      │  │    │  │ - embedding (vector)        │  │    │ │
│  │  │  │ keywords            │  │    │  │ - keywords (text)           │  │    │ │
│  │  │  │ resources           │  │    │  │ - description (text)        │  │    │ │
│  │  │  │ resource_mappings   │  │    │  └─────────────────────────────┘  │    │ │
│  │  │  │ mesh_concepts       │  │    └───────────────────────────────────┘    │ │
│  │  │  └─────────────────────┘  │                                              │ │
│  │  └───────────────────────────┘                                              │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                          │
│                                      ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                        Service Layer                                        │ │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐    │ │
│  │  │  TaxonomyService   │  │ ClassificationSvc  │  │   TaggingService   │    │ │
│  │  │  (Enhanced)        │  │ (Hybrid Search)    │  │ (AnKing Format)    │    │ │
│  │  └────────────────────┘  └────────────────────┘  └────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                          │
│                                      ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                        Export Layer                                         │ │
│  │     Anki Tags: #AK_Step1_v12::#FirstAid::Cardiology::HeartFailure          │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema Design

### 3.1 SQLite Schema (`packages/core/src/medanki/storage/taxonomy_schema.sql`)

```sql
-- ============================================================================
-- MedAnki Taxonomy Database Schema
-- Supports hierarchical taxonomies for MCAT and USMLE exams
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Core Tables
-- ----------------------------------------------------------------------------

-- Exams table: MCAT, USMLE_STEP1, USMLE_STEP2_CK, USMLE_STEP3
CREATE TABLE IF NOT EXISTS exams (
    id TEXT PRIMARY KEY,                    -- 'MCAT', 'USMLE_STEP1', etc.
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL,                  -- '2024', '2025'
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Taxonomy nodes: All taxonomy items in a closure table pattern
-- Supports unlimited hierarchy depth
CREATE TABLE IF NOT EXISTS taxonomy_nodes (
    id TEXT PRIMARY KEY,                    -- 'MCAT::FC1::1A::Proteins'
    exam_id TEXT NOT NULL REFERENCES exams(id),
    node_type TEXT NOT NULL,                -- 'section', 'foundational_concept', 'category', 
                                            -- 'topic', 'subtopic', 'system', 'discipline'
    code TEXT NOT NULL,                     -- 'FC1', '1A', 'SYS1', etc.
    title TEXT NOT NULL,
    description TEXT,
    percentage_weight REAL,                 -- For exam weighting (e.g., 25% biochem)
    sort_order INTEGER DEFAULT 0,
    metadata JSON,                          -- Flexible storage for extra attributes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(exam_id, code)
);

-- Taxonomy edges: Parent-child relationships (closure table)
-- Allows efficient ancestor/descendant queries
CREATE TABLE IF NOT EXISTS taxonomy_edges (
    ancestor_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    descendant_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    depth INTEGER NOT NULL,                 -- 0 = self, 1 = direct child, etc.
    path_string TEXT,                       -- 'FC1 > 1A > Proteins'
    
    PRIMARY KEY (ancestor_id, descendant_id)
);

-- Keywords associated with taxonomy nodes
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    keyword TEXT NOT NULL,
    keyword_type TEXT DEFAULT 'general',    -- 'general', 'abbreviation', 'synonym', 'researcher'
    weight REAL DEFAULT 1.0,                -- For keyword importance ranking
    
    UNIQUE(node_id, keyword)
);

-- Cross-classification mappings (for USMLE System × Discipline)
CREATE TABLE IF NOT EXISTS cross_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    secondary_node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    relationship_type TEXT NOT NULL,        -- 'system_discipline', 'topic_resource'
    weight REAL DEFAULT 1.0,
    
    UNIQUE(primary_node_id, secondary_node_id, relationship_type)
);

-- ----------------------------------------------------------------------------
-- External Resource Integration
-- ----------------------------------------------------------------------------

-- Study resources (First Aid, Pathoma, Sketchy, B&B, AnKing)
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,                    -- 'first_aid_2024', 'pathoma', etc.
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,            -- 'book', 'video', 'deck', 'qbank'
    version TEXT,
    url TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Resource sections/chapters
CREATE TABLE IF NOT EXISTS resource_sections (
    id TEXT PRIMARY KEY,                    -- 'first_aid::cardiology::heart_failure'
    resource_id TEXT NOT NULL REFERENCES resources(id),
    parent_section_id TEXT REFERENCES resource_sections(id),
    section_type TEXT NOT NULL,             -- 'chapter', 'section', 'video', 'card_group'
    code TEXT,                              -- 'Ch. 1', 'Video 3.2'
    title TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    duration_seconds INTEGER,               -- For videos
    sort_order INTEGER DEFAULT 0,
    metadata JSON
);

-- Mapping between taxonomy nodes and resource sections
CREATE TABLE IF NOT EXISTS resource_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    section_id TEXT NOT NULL REFERENCES resource_sections(id),
    relevance_score REAL DEFAULT 1.0,       -- 0.0-1.0
    is_primary BOOLEAN DEFAULT FALSE,       -- Primary resource for this topic
    
    UNIQUE(node_id, section_id)
);

-- ----------------------------------------------------------------------------
-- MeSH/UMLS Integration
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS mesh_concepts (
    mesh_id TEXT PRIMARY KEY,               -- 'D000328'
    name TEXT NOT NULL,
    tree_numbers TEXT,                      -- JSON array of tree numbers
    scope_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mesh_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id),
    mesh_id TEXT NOT NULL REFERENCES mesh_concepts(mesh_id),
    mapping_type TEXT DEFAULT 'exact',      -- 'exact', 'broader', 'narrower', 'related'
    confidence REAL DEFAULT 1.0,
    
    UNIQUE(node_id, mesh_id)
);

-- ----------------------------------------------------------------------------
-- AnKing Tag Integration
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS anking_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_path TEXT NOT NULL UNIQUE,          -- '#AK_Step1_v12::#FirstAid::Chapter1::Section'
    node_id TEXT REFERENCES taxonomy_nodes(id),
    resource_section_id TEXT REFERENCES resource_sections(id),
    card_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Indexes for Performance
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_nodes_exam ON taxonomy_nodes(exam_id);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON taxonomy_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_edges_ancestor ON taxonomy_edges(ancestor_id);
CREATE INDEX IF NOT EXISTS idx_edges_descendant ON taxonomy_edges(descendant_id);
CREATE INDEX IF NOT EXISTS idx_keywords_node ON keywords(node_id);
CREATE INDEX IF NOT EXISTS idx_keywords_text ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_resource_mappings_node ON resource_mappings(node_id);
CREATE INDEX IF NOT EXISTS idx_anking_tags_path ON anking_tags(tag_path);

-- ----------------------------------------------------------------------------
-- Views for Common Queries
-- ----------------------------------------------------------------------------

-- Full path view for any node
CREATE VIEW IF NOT EXISTS v_node_paths AS
SELECT 
    n.id,
    n.exam_id,
    n.code,
    n.title,
    n.node_type,
    GROUP_CONCAT(p.title, ' > ') AS full_path,
    MAX(e.depth) AS depth
FROM taxonomy_nodes n
JOIN taxonomy_edges e ON e.descendant_id = n.id
JOIN taxonomy_nodes p ON p.id = e.ancestor_id
GROUP BY n.id
ORDER BY n.exam_id, n.sort_order;

-- Keywords aggregated by node
CREATE VIEW IF NOT EXISTS v_node_keywords AS
SELECT 
    node_id,
    GROUP_CONCAT(keyword, ', ') AS all_keywords,
    COUNT(*) AS keyword_count
FROM keywords
GROUP BY node_id;
```

### 3.2 Pydantic Models (`packages/core/src/medanki/models/taxonomy.py`)

```python
"""Enhanced taxonomy models with full MCAT/USMLE support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ExamType(str, Enum):
    MCAT = "MCAT"
    USMLE_STEP1 = "USMLE_STEP1"
    USMLE_STEP2_CK = "USMLE_STEP2_CK"
    USMLE_STEP3 = "USMLE_STEP3"


class NodeType(str, Enum):
    # MCAT hierarchy
    SECTION = "section"                     # Bio/Biochem, Chem/Phys, Psych/Soc, CARS
    FOUNDATIONAL_CONCEPT = "foundational_concept"  # FC1-FC10
    CONTENT_CATEGORY = "content_category"   # 1A, 1B, etc.
    TOPIC = "topic"
    SUBTOPIC = "subtopic"
    
    # USMLE hierarchy
    ORGAN_SYSTEM = "organ_system"           # Cardiovascular, Respiratory, etc.
    DISCIPLINE = "discipline"               # Pathology, Physiology, etc.
    CLINICAL_PRESENTATION = "clinical_presentation"  # Chest pain, dyspnea, etc.
    DISEASE = "disease"


class ResourceType(str, Enum):
    BOOK = "book"
    VIDEO_SERIES = "video_series"
    ANKI_DECK = "anki_deck"
    QBANK = "qbank"
    LECTURE = "lecture"


@dataclass
class Keyword:
    """Keyword associated with a taxonomy node."""
    text: str
    keyword_type: str = "general"  # general, abbreviation, synonym, researcher
    weight: float = 1.0


@dataclass
class TaxonomyNode:
    """A node in the taxonomy hierarchy."""
    id: str
    exam_type: ExamType
    node_type: NodeType
    code: str
    title: str
    description: str | None = None
    keywords: list[Keyword] = field(default_factory=list)
    percentage_weight: float | None = None
    parent_id: str | None = None
    children: list[TaxonomyNode] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Computed fields
    path: str = ""
    depth: int = 0
    
    def get_all_keywords(self) -> list[str]:
        """Get all keyword strings."""
        return [k.text for k in self.keywords]
    
    def get_anking_tag(self) -> str:
        """Generate AnKing-compatible tag path."""
        parts = self.path.split(" > ")
        clean_parts = [p.replace(" ", "_").replace("/", "_") for p in parts]
        return f"#AK_{self.exam_type.value}::" + "::".join(clean_parts)


@dataclass
class ResourceSection:
    """A section within a study resource."""
    id: str
    resource_id: str
    title: str
    section_type: str
    code: str | None = None
    parent_id: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    duration_seconds: int | None = None


@dataclass
class ResourceMapping:
    """Mapping between a taxonomy node and resource section."""
    node_id: str
    section_id: str
    relevance_score: float = 1.0
    is_primary: bool = False


@dataclass
class CrossClassification:
    """Cross-classification for multi-dimensional taxonomy (e.g., USMLE System × Discipline)."""
    primary_node_id: str
    secondary_node_id: str
    relationship_type: str  # 'system_discipline'
    weight: float = 1.0
```

---

## 4. Comprehensive JSON Taxonomy Files

### 4.1 Enhanced MCAT Taxonomy (`data/taxonomies/mcat_complete.json`)

```json
{
  "$schema": "./taxonomy_schema.json",
  "exam": "MCAT",
  "version": "2024-2025",
  "source": "AAMC Content Outline",
  "source_url": "https://students-residents.aamc.org/media/9261/download",
  "sections": [
    {
      "id": "BIO_BIOCHEM",
      "code": "Section1",
      "title": "Biological and Biochemical Foundations of Living Systems",
      "description": "Tests understanding of basic biological processes and biochemistry",
      "questions": 59,
      "time_minutes": 95,
      "discipline_breakdown": {
        "Biochemistry": 0.25,
        "Biology": 0.65,
        "General Chemistry": 0.05,
        "Organic Chemistry": 0.05
      },
      "foundational_concepts": [
        {
          "id": "FC1",
          "code": "FC1",
          "title": "Biomolecules have unique properties that determine how they contribute to the structure and function of cells and how they participate in the processes necessary to maintain life",
          "percentage": 0.55,
          "keywords": ["biomolecules", "cells", "structure", "function", "metabolism"],
          "categories": [
            {
              "id": "1A",
              "code": "1A",
              "title": "Structure and function of proteins and their constituent amino acids",
              "discipline": "BC",
              "topics": [
                {
                  "id": "1A_AA",
                  "title": "Amino Acids",
                  "subtopics": [
                    "Description: α-amino acids; amino group, carboxyl group",
                    "Absolute configuration at the α position",
                    "Classification: acidic or basic, hydrophilic or hydrophobic",
                    "Amino acid abbreviations and structures",
                    "Zwitterion behavior and isoelectric point",
                    "Side chain reactivity and modifications"
                  ],
                  "keywords": [
                    "amino acid", "alpha carbon", "zwitterion", "isoelectric point",
                    "pKa", "acidic amino acid", "basic amino acid", "hydrophobic",
                    "hydrophilic", "polar", "nonpolar", "glycine", "proline",
                    "cysteine", "disulfide bond", "R group", "side chain"
                  ]
                },
                {
                  "id": "1A_PEPTIDE",
                  "title": "Peptide Bond Formation and Protein Structure",
                  "subtopics": [
                    "Peptide bond: polypeptides, proteins",
                    "Primary structure of proteins",
                    "Secondary structure: α-helix, β-pleated sheet",
                    "Tertiary structure: role of proline, cysteine, hydrophobic bonding",
                    "Quaternary structure"
                  ],
                  "keywords": [
                    "peptide bond", "primary structure", "secondary structure",
                    "tertiary structure", "quaternary structure", "alpha helix",
                    "beta sheet", "beta pleated sheet", "hydrogen bond",
                    "hydrophobic interaction", "disulfide bridge", "denaturation",
                    "protein folding", "chaperone", "prion"
                  ]
                },
                {
                  "id": "1A_ENZYME",
                  "title": "Enzyme Kinetics and Regulation",
                  "subtopics": [
                    "Enzyme classification by reaction type",
                    "Mechanism of catalysis: reduction of activation energy",
                    "Cofactors and coenzymes",
                    "Michaelis-Menten kinetics: Km, Vmax",
                    "Lineweaver-Burk plots",
                    "Competitive inhibition",
                    "Non-competitive inhibition",
                    "Uncompetitive inhibition",
                    "Mixed inhibition",
                    "Allosteric enzymes and regulation",
                    "Feedback regulation",
                    "Zymogen activation"
                  ],
                  "keywords": [
                    "enzyme", "substrate", "active site", "Michaelis-Menten",
                    "Km", "Vmax", "Lineweaver-Burk", "competitive inhibition",
                    "noncompetitive inhibition", "uncompetitive inhibition",
                    "allosteric", "cooperativity", "feedback inhibition",
                    "cofactor", "coenzyme", "NAD", "FAD", "zymogen", "proenzyme",
                    "activation energy", "transition state", "induced fit",
                    "lock and key"
                  ],
                  "formulas": [
                    "v = Vmax[S] / (Km + [S])",
                    "1/v = (Km/Vmax)(1/[S]) + 1/Vmax"
                  ]
                }
              ]
            },
            {
              "id": "1B",
              "code": "1B",
              "title": "Transmission of genetic information from the gene to the protein",
              "discipline": "BC",
              "topics": [
                {
                  "id": "1B_DNA",
                  "title": "DNA Structure and Replication",
                  "subtopics": [
                    "Nucleotide structure",
                    "Watson-Crick model, double helix",
                    "Base pairing and complementarity",
                    "Semiconservative replication",
                    "Replication enzymes: helicase, primase, DNA polymerase, ligase",
                    "Leading and lagging strand synthesis",
                    "Okazaki fragments",
                    "Proofreading and repair mechanisms"
                  ],
                  "keywords": [
                    "DNA", "nucleotide", "adenine", "guanine", "cytosine", "thymine",
                    "double helix", "Watson-Crick", "complementary base pairing",
                    "semiconservative", "replication fork", "helicase", "primase",
                    "DNA polymerase", "ligase", "leading strand", "lagging strand",
                    "Okazaki fragment", "proofreading", "mismatch repair"
                  ],
                  "researchers": ["Watson", "Crick", "Franklin", "Meselson", "Stahl"]
                },
                {
                  "id": "1B_TRANSCRIPTION",
                  "title": "Transcription",
                  "subtopics": [
                    "RNA polymerase and promoters",
                    "Initiation, elongation, termination",
                    "mRNA processing in eukaryotes",
                    "5' cap and 3' poly-A tail",
                    "Splicing: introns, exons, spliceosomes",
                    "Alternative splicing"
                  ],
                  "keywords": [
                    "transcription", "RNA polymerase", "promoter", "TATA box",
                    "initiation", "elongation", "termination", "mRNA", "pre-mRNA",
                    "5' cap", "poly-A tail", "splicing", "intron", "exon",
                    "spliceosome", "snRNP", "alternative splicing"
                  ]
                },
                {
                  "id": "1B_TRANSLATION",
                  "title": "Translation",
                  "subtopics": [
                    "Ribosome structure and function",
                    "tRNA structure, aminoacyl-tRNA synthetases",
                    "Initiation, elongation, termination codons",
                    "Wobble pairing",
                    "Post-translational modifications"
                  ],
                  "keywords": [
                    "translation", "ribosome", "tRNA", "mRNA", "codon", "anticodon",
                    "aminoacyl-tRNA synthetase", "start codon", "stop codon",
                    "AUG", "initiation", "elongation", "termination", "wobble",
                    "post-translational modification", "signal peptide"
                  ]
                },
                {
                  "id": "1B_RECOMBINANT",
                  "title": "Recombinant DNA and Biotechnology",
                  "subtopics": [
                    "Restriction enzymes",
                    "DNA cloning and vectors",
                    "PCR (Polymerase Chain Reaction)",
                    "Gel electrophoresis",
                    "Southern blotting",
                    "Sequencing techniques",
                    "CRISPR-Cas9"
                  ],
                  "keywords": [
                    "restriction enzyme", "sticky ends", "blunt ends", "plasmid",
                    "vector", "cloning", "PCR", "primer", "Taq polymerase",
                    "gel electrophoresis", "Southern blot", "Northern blot",
                    "Western blot", "sequencing", "Sanger", "CRISPR", "Cas9"
                  ]
                }
              ]
            },
            {
              "id": "1C",
              "code": "1C",
              "title": "Transmission of heritable information from generation to generation and the processes that increase genetic diversity",
              "discipline": "BIO",
              "topics": [
                {
                  "id": "1C_MENDELIAN",
                  "title": "Mendelian Genetics",
                  "subtopics": [
                    "Phenotype and genotype",
                    "Gene, allele, locus",
                    "Homozygous and heterozygous",
                    "Dominant and recessive traits",
                    "Complete dominance, incomplete dominance, codominance",
                    "Punnett squares and probability",
                    "Test cross and dihybrid cross",
                    "Sex-linked traits",
                    "Penetrance and expressivity"
                  ],
                  "keywords": [
                    "Mendel", "phenotype", "genotype", "allele", "locus", "gene",
                    "homozygous", "heterozygous", "dominant", "recessive",
                    "Punnett square", "test cross", "dihybrid", "monohybrid",
                    "sex-linked", "X-linked", "penetrance", "expressivity",
                    "codominance", "incomplete dominance"
                  ],
                  "researchers": ["Mendel"]
                },
                {
                  "id": "1C_MEIOSIS",
                  "title": "Meiosis and Genetic Variability",
                  "subtopics": [
                    "Meiosis I and II phases",
                    "Crossing over and recombination",
                    "Independent assortment",
                    "Linkage and mapping",
                    "Non-disjunction and aneuploidy"
                  ],
                  "keywords": [
                    "meiosis", "crossing over", "recombination", "synapsis",
                    "chiasma", "independent assortment", "linkage", "genetic map",
                    "non-disjunction", "aneuploidy", "trisomy", "monosomy",
                    "haploid", "diploid", "gamete"
                  ]
                },
                {
                  "id": "1C_EVOLUTION",
                  "title": "Evolution and Population Genetics",
                  "subtopics": [
                    "Natural selection",
                    "Fitness and adaptation",
                    "Hardy-Weinberg equilibrium",
                    "Conditions for Hardy-Weinberg",
                    "Genetic drift, bottleneck, founder effect",
                    "Gene flow and migration",
                    "Speciation"
                  ],
                  "keywords": [
                    "evolution", "natural selection", "fitness", "adaptation",
                    "Hardy-Weinberg", "p + q = 1", "p² + 2pq + q² = 1",
                    "genetic drift", "bottleneck effect", "founder effect",
                    "gene flow", "speciation", "reproductive isolation",
                    "Darwin"
                  ],
                  "formulas": [
                    "p + q = 1",
                    "p² + 2pq + q² = 1"
                  ],
                  "researchers": ["Darwin", "Hardy", "Weinberg"]
                }
              ]
            },
            {
              "id": "1D",
              "code": "1D",
              "title": "Principles of bioenergetics and fuel molecule metabolism",
              "discipline": "BC",
              "topics": [
                {
                  "id": "1D_THERMO",
                  "title": "Thermodynamics",
                  "subtopics": [
                    "Free energy (ΔG)",
                    "Spontaneity and equilibrium",
                    "ATP as energy currency",
                    "Coupled reactions",
                    "Phosphoryl group transfers"
                  ],
                  "keywords": [
                    "Gibbs free energy", "ΔG", "enthalpy", "entropy", "spontaneous",
                    "exergonic", "endergonic", "ATP", "ADP", "phosphorylation",
                    "coupled reaction", "equilibrium"
                  ],
                  "formulas": [
                    "ΔG = ΔH - TΔS",
                    "ΔG° = -RT ln Keq"
                  ]
                },
                {
                  "id": "1D_GLYCOLYSIS",
                  "title": "Glycolysis and Gluconeogenesis",
                  "subtopics": [
                    "Glycolysis: 10 steps, net ATP yield",
                    "Key enzymes: hexokinase, PFK-1, pyruvate kinase",
                    "Regulation of glycolysis",
                    "Gluconeogenesis bypass reactions",
                    "Cori cycle"
                  ],
                  "keywords": [
                    "glycolysis", "glucose", "pyruvate", "ATP", "NADH",
                    "hexokinase", "PFK-1", "phosphofructokinase", "pyruvate kinase",
                    "gluconeogenesis", "Cori cycle", "lactate", "anaerobic"
                  ]
                },
                {
                  "id": "1D_TCA",
                  "title": "Citric Acid Cycle (TCA/Krebs)",
                  "subtopics": [
                    "Pyruvate dehydrogenase complex",
                    "TCA cycle reactions and enzymes",
                    "NADH and FADH2 production",
                    "Regulation: isocitrate dehydrogenase, α-ketoglutarate dehydrogenase",
                    "Anaplerotic reactions"
                  ],
                  "keywords": [
                    "citric acid cycle", "TCA", "Krebs cycle", "acetyl-CoA",
                    "oxaloacetate", "citrate", "isocitrate", "α-ketoglutarate",
                    "succinate", "fumarate", "malate", "NADH", "FADH2", "GTP",
                    "pyruvate dehydrogenase"
                  ],
                  "researchers": ["Krebs"]
                },
                {
                  "id": "1D_ETC",
                  "title": "Electron Transport Chain and Oxidative Phosphorylation",
                  "subtopics": [
                    "ETC complexes I-IV",
                    "Electron carriers: NADH, FADH2, ubiquinone, cytochrome c",
                    "Proton gradient and chemiosmosis",
                    "ATP synthase mechanism",
                    "P/O ratio and ATP yield",
                    "Uncoupling agents"
                  ],
                  "keywords": [
                    "electron transport chain", "ETC", "oxidative phosphorylation",
                    "chemiosmosis", "ATP synthase", "proton gradient", "Complex I",
                    "Complex II", "Complex III", "Complex IV", "cytochrome c",
                    "ubiquinone", "coenzyme Q", "P/O ratio", "uncoupling"
                  ],
                  "researchers": ["Mitchell"]
                },
                {
                  "id": "1D_LIPID_MET",
                  "title": "Fatty Acid and Lipid Metabolism",
                  "subtopics": [
                    "Fatty acid oxidation (β-oxidation)",
                    "Carnitine shuttle",
                    "Ketone body synthesis and utilization",
                    "Fatty acid synthesis",
                    "Cholesterol synthesis and regulation"
                  ],
                  "keywords": [
                    "beta oxidation", "β-oxidation", "fatty acid", "acetyl-CoA",
                    "carnitine", "CPT-I", "CPT-II", "ketone bodies",
                    "acetoacetate", "β-hydroxybutyrate", "ketogenesis",
                    "fatty acid synthase", "malonyl-CoA", "cholesterol", "HMG-CoA"
                  ]
                }
              ]
            }
          ]
        },
        {
          "id": "FC2",
          "code": "FC2",
          "title": "Highly organized assemblies of molecules, cells, and organs interact to carry out the functions of living organisms",
          "percentage": 0.20,
          "keywords": ["cells", "organs", "assemblies", "organisms", "tissues"],
          "categories": [
            {
              "id": "2A",
              "code": "2A",
              "title": "Assemblies of molecules, cells, and groups of cells within single cellular and multicellular organisms",
              "discipline": "BIO",
              "topics": [
                {
                  "id": "2A_MEMBRANE",
                  "title": "Plasma Membrane",
                  "subtopics": [
                    "Fluid mosaic model",
                    "Phospholipid bilayer composition",
                    "Membrane proteins: integral, peripheral",
                    "Membrane transport: passive, facilitated, active",
                    "Na+/K+ ATPase",
                    "Osmosis, tonicity",
                    "Endocytosis, exocytosis"
                  ],
                  "keywords": [
                    "plasma membrane", "phospholipid bilayer", "fluid mosaic",
                    "integral protein", "peripheral protein", "channel", "carrier",
                    "passive transport", "facilitated diffusion", "active transport",
                    "Na/K ATPase", "osmosis", "hypertonic", "hypotonic", "isotonic",
                    "endocytosis", "exocytosis", "pinocytosis", "phagocytosis"
                  ],
                  "researchers": ["Singer", "Nicolson"]
                },
                {
                  "id": "2A_ORGANELLES",
                  "title": "Organelles and Cellular Components",
                  "subtopics": [
                    "Nucleus and nuclear envelope",
                    "Endoplasmic reticulum (rough and smooth)",
                    "Golgi apparatus",
                    "Lysosomes and peroxisomes",
                    "Mitochondria structure and function",
                    "Cytoskeleton: microfilaments, intermediate filaments, microtubules"
                  ],
                  "keywords": [
                    "nucleus", "nucleolus", "nuclear envelope", "nuclear pore",
                    "rough ER", "smooth ER", "Golgi", "lysosome", "peroxisome",
                    "mitochondria", "matrix", "cristae", "cytoskeleton",
                    "microfilament", "actin", "intermediate filament", "microtubule",
                    "tubulin", "centrosome", "centriole"
                  ]
                }
              ]
            },
            {
              "id": "2B",
              "code": "2B",
              "title": "The structure, growth, physiology, and genetics of prokaryotes and viruses",
              "discipline": "BIO",
              "topics": [
                {
                  "id": "2B_BACTERIA",
                  "title": "Prokaryotic Cell Structure",
                  "subtopics": [
                    "Cell wall: peptidoglycan, Gram positive/negative",
                    "Plasma membrane",
                    "Flagella and motility",
                    "Plasmids and antibiotic resistance",
                    "Binary fission",
                    "Transformation, transduction, conjugation"
                  ],
                  "keywords": [
                    "prokaryote", "bacteria", "peptidoglycan", "Gram positive",
                    "Gram negative", "flagellum", "pilus", "plasmid", "binary fission",
                    "transformation", "transduction", "conjugation", "F plasmid",
                    "antibiotic resistance"
                  ]
                },
                {
                  "id": "2B_VIRUS",
                  "title": "Viral Structure and Life Cycles",
                  "subtopics": [
                    "Virus structure: capsid, envelope, genome",
                    "Lytic vs lysogenic cycle",
                    "Bacteriophage",
                    "Retroviruses and reverse transcriptase",
                    "Prions"
                  ],
                  "keywords": [
                    "virus", "capsid", "envelope", "lytic cycle", "lysogenic cycle",
                    "bacteriophage", "prophage", "retrovirus", "reverse transcriptase",
                    "HIV", "RNA virus", "DNA virus", "prion"
                  ]
                }
              ]
            },
            {
              "id": "2C",
              "code": "2C",
              "title": "Processes of cell division, differentiation, and specialization",
              "discipline": "BIO",
              "topics": [
                {
                  "id": "2C_CELL_CYCLE",
                  "title": "Cell Cycle and Mitosis",
                  "subtopics": [
                    "Interphase: G1, S, G2",
                    "Mitosis phases: prophase, metaphase, anaphase, telophase",
                    "Cytokinesis",
                    "Cell cycle regulation: cyclins, CDKs",
                    "Checkpoints: G1, G2, M",
                    "Cancer and cell cycle dysregulation"
                  ],
                  "keywords": [
                    "cell cycle", "interphase", "G1", "S phase", "G2", "mitosis",
                    "prophase", "metaphase", "anaphase", "telophase", "cytokinesis",
                    "cyclin", "CDK", "checkpoint", "p53", "Rb", "cancer", "tumor"
                  ]
                },
                {
                  "id": "2C_EMBRYO",
                  "title": "Embryogenesis and Development",
                  "subtopics": [
                    "Fertilization",
                    "Cleavage and blastula formation",
                    "Gastrulation: ectoderm, mesoderm, endoderm",
                    "Organogenesis",
                    "Stem cells and differentiation",
                    "Apoptosis"
                  ],
                  "keywords": [
                    "fertilization", "zygote", "cleavage", "morula", "blastula",
                    "blastocyst", "gastrulation", "ectoderm", "mesoderm", "endoderm",
                    "germ layer", "organogenesis", "stem cell", "pluripotent",
                    "totipotent", "differentiation", "apoptosis"
                  ]
                }
              ]
            }
          ]
        },
        {
          "id": "FC3",
          "code": "FC3",
          "title": "Complex systems of tissues and organs sense the internal and external environments of multicellular organisms, and through integrated functioning, maintain a stable internal environment within an ever-changing external environment",
          "percentage": 0.25,
          "keywords": ["tissues", "organs", "nervous system", "endocrine", "homeostasis"],
          "categories": [
            {
              "id": "3A",
              "code": "3A",
              "title": "Structure and functions of the nervous and endocrine systems and ways in which these systems coordinate the organ systems",
              "discipline": "BIO",
              "topics": []
            },
            {
              "id": "3B",
              "code": "3B",
              "title": "Structure and integrative functions of the main organ systems",
              "discipline": "BIO",
              "topics": []
            }
          ]
        }
      ]
    },
    {
      "id": "CHEM_PHYS",
      "code": "Section2",
      "title": "Chemical and Physical Foundations of Biological Systems",
      "questions": 59,
      "time_minutes": 95,
      "discipline_breakdown": {
        "Biochemistry": 0.25,
        "Biology": 0.05,
        "General Chemistry": 0.30,
        "Organic Chemistry": 0.15,
        "Physics": 0.25
      },
      "foundational_concepts": [
        {
          "id": "FC4",
          "code": "FC4",
          "title": "Complex living organisms transport materials, sense their environment, process signals, and respond to changes using processes that can be understood in terms of physical principles",
          "percentage": 0.40,
          "categories": []
        },
        {
          "id": "FC5",
          "code": "FC5",
          "title": "The principles that govern chemical interactions and reactions form the basis for a broader understanding of the molecular dynamics of living systems",
          "percentage": 0.60,
          "categories": []
        }
      ]
    },
    {
      "id": "PSYCH_SOC",
      "code": "Section3",
      "title": "Psychological, Social, and Biological Foundations of Behavior",
      "questions": 59,
      "time_minutes": 95,
      "discipline_breakdown": {
        "Psychology": 0.65,
        "Sociology": 0.30,
        "Biology": 0.05
      },
      "foundational_concepts": [
        {
          "id": "FC6",
          "code": "FC6",
          "title": "Biological, psychological, and sociocultural factors influence the ways that individuals perceive, think about, and react to the world",
          "percentage": 0.25,
          "categories": []
        },
        {
          "id": "FC7",
          "code": "FC7",
          "title": "Biological, psychological, and sociocultural factors influence behavior and behavior change",
          "percentage": 0.35,
          "categories": []
        },
        {
          "id": "FC8",
          "code": "FC8",
          "title": "Psychological, sociocultural, and biological factors influence the way we think about ourselves and others, as well as how we interact with others",
          "percentage": 0.20,
          "categories": []
        },
        {
          "id": "FC9",
          "code": "FC9",
          "title": "Cultural and social differences influence well-being",
          "percentage": 0.15,
          "categories": []
        },
        {
          "id": "FC10",
          "code": "FC10",
          "title": "Social stratification and access to resources influence well-being",
          "percentage": 0.05,
          "categories": []
        }
      ]
    },
    {
      "id": "CARS",
      "code": "Section4",
      "title": "Critical Analysis and Reasoning Skills",
      "questions": 53,
      "time_minutes": 90,
      "description": "Skills-based section without content outline - tests reading comprehension and reasoning"
    }
  ],
  "key_researchers": {
    "Psychology": ["Pavlov", "Skinner", "Bandura", "Piaget", "Vygotsky", "Erikson", "Freud", "Maslow", "Rogers", "Kohlberg", "Milgram", "Asch", "Zimbardo", "Bowlby", "Ainsworth", "Chomsky", "Loftus", "Ebbinghaus"],
    "Sociology": ["Durkheim", "Marx", "Weber", "Mead", "Goffman", "Cooley", "Bourdieu", "Parsons", "Blumer"],
    "Biology": ["Darwin", "Mendel", "Watson", "Crick", "Franklin", "Meselson", "Stahl"],
    "Biochemistry": ["Krebs", "Mitchell"]
  }
}
```

### 4.2 Enhanced USMLE Step 1 Taxonomy (`data/taxonomies/usmle_step1_complete.json`)

This is a much larger file. I'll show the structure with one complete system example:

```json
{
  "$schema": "./taxonomy_schema.json",
  "exam": "USMLE_STEP1",
  "version": "2024",
  "source": "NBME Content Outline",
  "source_url": "https://www.usmle.org/exam-resources/step-1-materials",
  "distributions": {
    "organ_systems": {
      "Human Development": {"min": 0.01, "max": 0.03},
      "Blood & Lymphoreticular/Immune Systems": {"min": 0.09, "max": 0.13},
      "Behavioral Health & Nervous Systems/Special Senses": {"min": 0.10, "max": 0.14},
      "Musculoskeletal, Skin & Subcutaneous Tissue": {"min": 0.08, "max": 0.12},
      "Cardiovascular System": {"min": 0.07, "max": 0.11},
      "Respiratory & Renal/Urinary Systems": {"min": 0.11, "max": 0.15},
      "Gastrointestinal System": {"min": 0.06, "max": 0.10},
      "Reproductive & Endocrine Systems": {"min": 0.12, "max": 0.16},
      "Multisystem Processes & Disorders": {"min": 0.08, "max": 0.12},
      "Biostatistics & Epidemiology": {"min": 0.04, "max": 0.06},
      "Social Sciences": {"min": 0.06, "max": 0.09}
    },
    "disciplines": {
      "Pathology": {"min": 0.45, "max": 0.55},
      "Physiology": {"min": 0.30, "max": 0.40},
      "Pharmacology": {"min": 0.10, "max": 0.20},
      "Biochemistry & Nutrition": {"min": 0.05, "max": 0.15},
      "Microbiology": {"min": 0.10, "max": 0.20},
      "Immunology": {"min": 0.05, "max": 0.15},
      "Gross Anatomy & Embryology": {"min": 0.10, "max": 0.20},
      "Histology & Cell Biology": {"min": 0.05, "max": 0.15},
      "Behavioral Sciences": {"min": 0.10, "max": 0.15},
      "Genetics": {"min": 0.05, "max": 0.10}
    }
  },
  "organ_systems": [
    {
      "id": "CARDIO",
      "code": "Cardiovascular",
      "title": "Cardiovascular System",
      "nbme_chapter": "Cardiovascular System",
      "first_aid_chapter": "Cardiovascular",
      "pathoma_chapters": ["Chapter 07", "Chapter 08"],
      "keywords": ["heart", "cardiovascular", "blood vessels", "circulation", "cardiac"],
      "topics": [
        {
          "id": "CARDIO_ANATOMY",
          "title": "Cardiac Anatomy",
          "discipline": "Anatomy",
          "subtopics": [
            {
              "id": "CARDIO_ANATOMY_CHAMBERS",
              "title": "Heart Chambers and Valves",
              "keywords": ["atrium", "ventricle", "mitral valve", "tricuspid", "aortic valve", "pulmonary valve"],
              "first_aid_page": 281,
              "sketchy_video": null,
              "boards_beyond": "Cardiology::Cardiac Anatomy"
            },
            {
              "id": "CARDIO_ANATOMY_CORONARY",
              "title": "Coronary Circulation",
              "keywords": ["coronary artery", "LAD", "circumflex", "RCA", "coronary sinus"],
              "first_aid_page": 282
            }
          ]
        },
        {
          "id": "CARDIO_PHYSIO",
          "title": "Cardiac Physiology",
          "discipline": "Physiology",
          "subtopics": [
            {
              "id": "CARDIO_PHYSIO_CYCLE",
              "title": "Cardiac Cycle",
              "keywords": ["systole", "diastole", "preload", "afterload", "contractility", "stroke volume", "cardiac output"],
              "formulas": ["CO = SV × HR", "SV = EDV - ESV", "EF = SV/EDV"],
              "first_aid_page": 283
            },
            {
              "id": "CARDIO_PHYSIO_PRESSURE",
              "title": "Pressure-Volume Loops",
              "keywords": ["PV loop", "starling curve", "compliance"],
              "first_aid_page": 284
            },
            {
              "id": "CARDIO_PHYSIO_ACTION_POTENTIAL",
              "title": "Cardiac Action Potentials",
              "keywords": ["pacemaker", "SA node", "AV node", "depolarization", "repolarization", "phase 0", "phase 4"],
              "first_aid_page": 285
            }
          ]
        },
        {
          "id": "CARDIO_PATH",
          "title": "Cardiac Pathology",
          "discipline": "Pathology",
          "subtopics": [
            {
              "id": "CARDIO_PATH_CAD",
              "title": "Coronary Artery Disease",
              "keywords": ["atherosclerosis", "myocardial infarction", "MI", "STEMI", "NSTEMI", "angina", "troponin"],
              "pathoma_chapter": "Chapter 08",
              "sketchy_path": "SketchyPath::Cardio::CAD",
              "uworld_yield": "high"
            },
            {
              "id": "CARDIO_PATH_HF",
              "title": "Heart Failure",
              "keywords": ["CHF", "HFrEF", "HFpEF", "systolic dysfunction", "diastolic dysfunction", "S3", "S4", "JVD", "BNP"],
              "pathoma_chapter": "Chapter 08",
              "sketchy_path": "SketchyPath::Cardio::HeartFailure"
            },
            {
              "id": "CARDIO_PATH_VALVULAR",
              "title": "Valvular Disorders",
              "keywords": ["aortic stenosis", "aortic regurgitation", "mitral stenosis", "mitral regurgitation", "murmur", "rheumatic heart disease"],
              "pathoma_chapter": "Chapter 08"
            },
            {
              "id": "CARDIO_PATH_CARDIOMYOPATHY",
              "title": "Cardiomyopathies",
              "keywords": ["dilated cardiomyopathy", "hypertrophic cardiomyopathy", "HCM", "HOCM", "restrictive cardiomyopathy", "amyloidosis"],
              "pathoma_chapter": "Chapter 08"
            }
          ]
        },
        {
          "id": "CARDIO_PHARM",
          "title": "Cardiovascular Pharmacology",
          "discipline": "Pharmacology",
          "subtopics": [
            {
              "id": "CARDIO_PHARM_ANTIHTN",
              "title": "Antihypertensives",
              "keywords": ["ACE inhibitor", "ARB", "calcium channel blocker", "beta blocker", "thiazide", "hydralazine"],
              "sketchy_pharm": "SketchyPharm::Cardio::Antihypertensives",
              "first_aid_page": 310
            },
            {
              "id": "CARDIO_PHARM_ANTIARRHYTHMIC",
              "title": "Antiarrhythmics",
              "keywords": ["class I", "class II", "class III", "class IV", "amiodarone", "lidocaine", "procainamide"],
              "sketchy_pharm": "SketchyPharm::Cardio::Antiarrhythmics"
            },
            {
              "id": "CARDIO_PHARM_CHF",
              "title": "Heart Failure Drugs",
              "keywords": ["digoxin", "loop diuretic", "spironolactone", "sacubitril", "milrinone"],
              "sketchy_pharm": "SketchyPharm::Cardio::CHF"
            }
          ]
        },
        {
          "id": "CARDIO_MICRO",
          "title": "Cardiovascular Microbiology",
          "discipline": "Microbiology",
          "subtopics": [
            {
              "id": "CARDIO_MICRO_ENDOCARDITIS",
              "title": "Infective Endocarditis",
              "keywords": ["endocarditis", "Strep viridans", "Staph aureus", "HACEK", "Osler nodes", "Janeway lesions", "vegetation"],
              "sketchy_micro": "SketchyMicro::Bacteria::EndocarditisOrganisms"
            },
            {
              "id": "CARDIO_MICRO_RHEUMATIC",
              "title": "Rheumatic Fever",
              "keywords": ["Group A Strep", "GAS", "Jones criteria", "Aschoff bodies", "rheumatic heart disease"],
              "sketchy_micro": "SketchyMicro::Bacteria::GAS"
            }
          ]
        }
      ]
    }
  ],
  "disciplines": [
    {
      "id": "DISC_PATH",
      "code": "Pathology",
      "title": "Pathology",
      "percentage_range": {"min": 0.45, "max": 0.55},
      "description": "General pathology and disease mechanisms",
      "core_concepts": [
        "Cell injury and death",
        "Inflammation",
        "Hemodynamics",
        "Neoplasia",
        "Genetic disorders"
      ],
      "pathoma_chapters": ["01", "02", "03"]
    },
    {
      "id": "DISC_PHYSIO",
      "code": "Physiology",
      "title": "Physiology",
      "percentage_range": {"min": 0.30, "max": 0.40},
      "resources": ["Costanzo Physiology", "BRS Physiology"]
    },
    {
      "id": "DISC_PHARM",
      "code": "Pharmacology",
      "title": "Pharmacology",
      "percentage_range": {"min": 0.10, "max": 0.20},
      "resources": ["Sketchy Pharm", "First Aid Pharmacology"]
    },
    {
      "id": "DISC_BIOCHEM",
      "code": "Biochemistry",
      "title": "Biochemistry & Nutrition",
      "percentage_range": {"min": 0.05, "max": 0.15},
      "resources": ["Sketchy Biochem", "First Aid Biochemistry"]
    },
    {
      "id": "DISC_MICRO",
      "code": "Microbiology",
      "title": "Microbiology",
      "percentage_range": {"min": 0.10, "max": 0.20},
      "resources": ["Sketchy Micro", "First Aid Microbiology"]
    },
    {
      "id": "DISC_IMMUNO",
      "code": "Immunology",
      "title": "Immunology",
      "percentage_range": {"min": 0.05, "max": 0.15}
    },
    {
      "id": "DISC_ANATOMY",
      "code": "Anatomy",
      "title": "Gross Anatomy & Embryology",
      "percentage_range": {"min": 0.10, "max": 0.20}
    },
    {
      "id": "DISC_HISTO",
      "code": "Histology",
      "title": "Histology & Cell Biology",
      "percentage_range": {"min": 0.05, "max": 0.15}
    },
    {
      "id": "DISC_BEHAV",
      "code": "Behavioral",
      "title": "Behavioral Sciences",
      "percentage_range": {"min": 0.10, "max": 0.15}
    },
    {
      "id": "DISC_GENETICS",
      "code": "Genetics",
      "title": "Genetics",
      "percentage_range": {"min": 0.05, "max": 0.10}
    }
  ],
  "resources": {
    "first_aid": {
      "id": "first_aid_2024",
      "name": "First Aid for USMLE Step 1 2024",
      "type": "book",
      "anking_tag_prefix": "#AK_Step1_v12::#FirstAid"
    },
    "pathoma": {
      "id": "pathoma",
      "name": "Pathoma (Fundamentals of Pathology)",
      "type": "video_series",
      "chapters": 19,
      "anking_tag_prefix": "#AK_Step1_v12::#Pathoma"
    },
    "sketchy_micro": {
      "id": "sketchy_micro",
      "name": "Sketchy Medical - Microbiology",
      "type": "video_series",
      "anking_tag_prefix": "#AK_Step1_v12::#SketchyMicro"
    },
    "sketchy_pharm": {
      "id": "sketchy_pharm",
      "name": "Sketchy Medical - Pharmacology",
      "type": "video_series",
      "anking_tag_prefix": "#AK_Step1_v12::#SketchyPharm"
    },
    "sketchy_path": {
      "id": "sketchy_path",
      "name": "Sketchy Medical - Pathology",
      "type": "video_series",
      "anking_tag_prefix": "#AK_Step1_v12::#SketchyPath"
    },
    "boards_beyond": {
      "id": "boards_beyond",
      "name": "Boards and Beyond",
      "type": "video_series",
      "categories": 22,
      "anking_tag_prefix": "#AK_Step1_v12::#B&B"
    },
    "anking": {
      "id": "anking_step1_v12",
      "name": "AnKing Step 1 V12",
      "type": "anki_deck",
      "cards": 28000,
      "tag_hierarchy": "#AK_Step1_v12"
    }
  },
  "cross_mappings": {
    "system_discipline_examples": [
      {
        "system": "CARDIO",
        "discipline": "Pathology",
        "topics": ["CAD", "Heart Failure", "Valvular Disease"],
        "uworld_yield": "high"
      },
      {
        "system": "CARDIO",
        "discipline": "Pharmacology",
        "topics": ["Antihypertensives", "Antiarrhythmics", "CHF drugs"],
        "sketchy_coverage": true
      }
    ]
  }
}
```

---

## 5. Data Ingestion Scripts

### 5.1 Script Directory Structure

```
medanki/
├── scripts/
│   ├── __init__.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── base.py              # Base ingestion classes
│   │   ├── aamc_mcat.py         # MCAT content outline parser
│   │   ├── nbme_usmle.py        # USMLE content outline parser
│   │   ├── huggingface.py       # Hugging Face dataset loader
│   │   ├── anking_export.py     # AnKing CrowdAnki export parser
│   │   ├── mesh_api.py          # MeSH vocabulary API client
│   │   └── first_aid_parser.py  # First Aid PDF parser (future)
│   ├── build_taxonomy_db.py     # Main script to build SQLite DB
│   ├── sync_weaviate.py         # Sync taxonomy to vector store
│   └── validate_taxonomy.py     # Validation and testing
```

### 5.2 Hugging Face Dataset Ingestion (`scripts/ingest/huggingface.py`)

```python
"""
Ingest medical Q&A datasets from Hugging Face for taxonomy enrichment.

Datasets:
- medalpaca/medical_meadow_medical_flashcards: 33,955 Q&A pairs
- GBaker/MedQA-USMLE-4-options: USMLE-style questions
- openlifescienceai/medmcqa: 2,400+ medical topics
- lavita/medical-qa-datasets: Aggregated medical QA
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from datasets import load_dataset


@dataclass
class MedicalQAPair:
    """A medical question-answer pair from Hugging Face."""
    question: str
    answer: str
    source: str
    topic: str | None = None
    keywords: list[str] | None = None
    metadata: dict[str, Any] | None = None


class HuggingFaceIngestor:
    """Ingest medical education datasets from Hugging Face."""
    
    DATASETS = {
        "medical_flashcards": {
            "repo": "medalpaca/medical_meadow_medical_flashcards",
            "split": "train",
            "question_field": "input",
            "answer_field": "output",
        },
        "medqa_usmle": {
            "repo": "GBaker/MedQA-USMLE-4-options",
            "split": "train",
            "question_field": "question",
            "answer_field": "answer",
        },
        "medmcqa": {
            "repo": "openlifescienceai/medmcqa",
            "split": "train",
            "question_field": "question",
            "answer_field": "cop",  # correct option
        },
    }
    
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "medanki" / "hf"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_medical_flashcards(self, limit: int | None = None) -> Iterator[MedicalQAPair]:
        """Load medical flashcards dataset."""
        config = self.DATASETS["medical_flashcards"]
        dataset = load_dataset(
            config["repo"],
            split=config["split"],
            cache_dir=str(self.cache_dir),
        )
        
        for i, row in enumerate(dataset):
            if limit and i >= limit:
                break
            
            yield MedicalQAPair(
                question=row.get(config["question_field"], ""),
                answer=row.get(config["answer_field"], ""),
                source="medical_meadow_flashcards",
                metadata={"instruction": row.get("instruction", "")},
            )
    
    def load_medqa_usmle(self, limit: int | None = None) -> Iterator[MedicalQAPair]:
        """Load MedQA USMLE-style questions."""
        config = self.DATASETS["medqa_usmle"]
        dataset = load_dataset(
            config["repo"],
            split=config["split"],
            cache_dir=str(self.cache_dir),
        )
        
        for i, row in enumerate(dataset):
            if limit and i >= limit:
                break
            
            # Extract answer from options
            answer_idx = row.get("answer_idx", 0)
            options = row.get("options", {})
            answer = options.get(str(answer_idx), "")
            
            yield MedicalQAPair(
                question=row.get("question", ""),
                answer=answer,
                source="medqa_usmle",
                metadata={
                    "options": options,
                    "answer_idx": answer_idx,
                    "meta_info": row.get("meta_info", ""),
                },
            )
    
    def extract_topics_from_qa(
        self,
        qa_pairs: Iterator[MedicalQAPair],
        keyword_extractor: callable,
    ) -> dict[str, list[str]]:
        """
        Extract topic keywords from Q&A pairs.
        
        Returns a dict mapping extracted topics to associated keywords.
        """
        topic_keywords: dict[str, set[str]] = {}
        
        for qa in qa_pairs:
            combined_text = f"{qa.question} {qa.answer}"
            keywords = keyword_extractor(combined_text)
            
            for keyword in keywords:
                if keyword not in topic_keywords:
                    topic_keywords[keyword] = set()
                topic_keywords[keyword].update(keywords)
        
        return {k: list(v) for k, v in topic_keywords.items()}
    
    def save_to_jsonl(
        self,
        qa_pairs: Iterator[MedicalQAPair],
        output_path: Path,
    ) -> int:
        """Save Q&A pairs to JSONL file for later processing."""
        count = 0
        with open(output_path, "w") as f:
            for qa in qa_pairs:
                f.write(json.dumps({
                    "question": qa.question,
                    "answer": qa.answer,
                    "source": qa.source,
                    "topic": qa.topic,
                    "keywords": qa.keywords,
                    "metadata": qa.metadata,
                }) + "\n")
                count += 1
        return count


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest Hugging Face medical datasets")
    parser.add_argument("--dataset", choices=["flashcards", "medqa", "all"], default="all")
    parser.add_argument("--output", type=Path, default=Path("data/hf_medical_qa.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    ingestor = HuggingFaceIngestor()
    
    if args.dataset in ["flashcards", "all"]:
        print("Loading medical flashcards...")
        pairs = ingestor.load_medical_flashcards(limit=args.limit)
        count = ingestor.save_to_jsonl(pairs, args.output.with_suffix(".flashcards.jsonl"))
        print(f"Saved {count} flashcard pairs")
    
    if args.dataset in ["medqa", "all"]:
        print("Loading MedQA USMLE...")
        pairs = ingestor.load_medqa_usmle(limit=args.limit)
        count = ingestor.save_to_jsonl(pairs, args.output.with_suffix(".medqa.jsonl"))
        print(f"Saved {count} MedQA pairs")
```

### 5.3 AnKing Tag Export Parser (`scripts/ingest/anking_export.py`)

```python
"""
Parse AnKing deck exports from CrowdAnki add-on to extract tag hierarchy.

AnKing tag format: #AK_Step1_v12::#Resource::Chapter::Section::Subsection
Separator: :: (hierarchical delimiter)

Usage:
1. Install CrowdAnki add-on (code: 1788670778) in Anki
2. Export AnKing deck: File > Export > CrowdAnki JSON
3. Run this script on the exported JSON
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class AnkiNote:
    """An Anki note with tags."""
    guid: str
    fields: list[str]
    tags: list[str]


@dataclass
class TagNode:
    """A node in the tag hierarchy."""
    name: str
    full_path: str
    children: dict[str, TagNode] = field(default_factory=dict)
    note_count: int = 0
    
    def add_child(self, child_name: str) -> TagNode:
        if child_name not in self.children:
            child_path = f"{self.full_path}::{child_name}" if self.full_path else child_name
            self.children[child_name] = TagNode(name=child_name, full_path=child_path)
        return self.children[child_name]


class AnKingExportParser:
    """Parse AnKing CrowdAnki exports."""
    
    # Known resource prefixes in AnKing
    RESOURCE_PREFIXES = {
        "#AK_Step1_v12::#B&B": "Boards & Beyond",
        "#AK_Step1_v12::#Costanzo": "Costanzo Physiology",
        "#AK_Step1_v12::#FirstAid": "First Aid",
        "#AK_Step1_v12::#NBME": "NBME Practice Exams",
        "#AK_Step1_v12::#OME": "OnlineMedEd",
        "#AK_Step1_v12::#Pathoma": "Pathoma",
        "#AK_Step1_v12::#Physeo": "Physeo",
        "#AK_Step1_v12::#Pixorize": "Pixorize",
        "#AK_Step1_v12::#SketchyMicro": "Sketchy Micro",
        "#AK_Step1_v12::#SketchyPharm": "Sketchy Pharm",
        "#AK_Step1_v12::#SketchyPath": "Sketchy Path",
        "#AK_Step1_v12::#SketchyBiochem": "Sketchy Biochem",
        "#AK_Step1_v12::#UWorld": "UWorld",
    }
    
    def __init__(self):
        self.tag_tree: dict[str, TagNode] = {}
        self.all_tags: set[str] = set()
        self.tag_counts: dict[str, int] = defaultdict(int)
    
    def parse_export(self, export_path: Path) -> None:
        """Parse a CrowdAnki JSON export."""
        with open(export_path) as f:
            data = json.load(f)
        
        notes = data.get("notes", [])
        for note_data in notes:
            note = self._parse_note(note_data)
            self._process_tags(note.tags)
    
    def _parse_note(self, note_data: dict[str, Any]) -> AnkiNote:
        """Parse a single note from export."""
        return AnkiNote(
            guid=note_data.get("guid", ""),
            fields=[f.get("value", "") for f in note_data.get("fields", [])],
            tags=note_data.get("tags", []),
        )
    
    def _process_tags(self, tags: list[str]) -> None:
        """Process tags and build hierarchy."""
        for tag in tags:
            self.all_tags.add(tag)
            self.tag_counts[tag] += 1
            
            # Build hierarchy for AK tags
            if tag.startswith("#AK_"):
                self._add_to_tree(tag)
    
    def _add_to_tree(self, tag: str) -> None:
        """Add a tag to the hierarchical tree."""
        parts = tag.split("::")
        
        root_key = parts[0]
        if root_key not in self.tag_tree:
            self.tag_tree[root_key] = TagNode(name=root_key, full_path=root_key)
        
        current = self.tag_tree[root_key]
        current.note_count += 1
        
        for part in parts[1:]:
            current = current.add_child(part)
            current.note_count += 1
    
    def get_resource_tags(self, resource_prefix: str) -> list[str]:
        """Get all tags for a specific resource."""
        return sorted([t for t in self.all_tags if t.startswith(resource_prefix)])
    
    def get_tag_hierarchy(self) -> dict:
        """Get the full tag hierarchy as a nested dict."""
        def node_to_dict(node: TagNode) -> dict:
            result = {
                "name": node.name,
                "path": node.full_path,
                "count": node.note_count,
            }
            if node.children:
                result["children"] = {
                    k: node_to_dict(v) for k, v in node.children.items()
                }
            return result
        
        return {k: node_to_dict(v) for k, v in self.tag_tree.items()}
    
    def export_tag_mappings(self, output_path: Path) -> None:
        """Export tag mappings to JSON."""
        mappings = {
            "total_tags": len(self.all_tags),
            "resource_counts": {
                resource: sum(1 for t in self.all_tags if t.startswith(prefix))
                for prefix, resource in self.RESOURCE_PREFIXES.items()
            },
            "hierarchy": self.get_tag_hierarchy(),
            "tag_counts": dict(sorted(
                self.tag_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:1000]),  # Top 1000 tags
        }
        
        with open(output_path, "w") as f:
            json.dump(mappings, f, indent=2)
    
    def generate_taxonomy_mappings(self) -> dict[str, dict]:
        """
        Generate mappings from AnKing tags to taxonomy nodes.
        
        Returns a dict mapping tag paths to suggested taxonomy node IDs.
        """
        mappings = {}
        
        for tag, count in self.tag_counts.items():
            if not tag.startswith("#AK_Step1"):
                continue
            
            parts = tag.split("::")
            if len(parts) < 3:
                continue
            
            resource = parts[1].lstrip("#")
            
            # Map to taxonomy based on resource structure
            if resource == "FirstAid":
                # FirstAid chapters map to organ systems
                chapter = parts[2] if len(parts) > 2 else None
                mappings[tag] = {
                    "resource": "first_aid",
                    "chapter": chapter,
                    "sections": parts[3:] if len(parts) > 3 else [],
                    "card_count": count,
                }
            
            elif resource == "Pathoma":
                chapter_num = parts[2] if len(parts) > 2 else None
                mappings[tag] = {
                    "resource": "pathoma",
                    "chapter": chapter_num,
                    "sections": parts[3:] if len(parts) > 3 else [],
                    "card_count": count,
                }
            
            elif resource.startswith("Sketchy"):
                sketchy_type = resource.replace("Sketchy", "").lower()
                mappings[tag] = {
                    "resource": f"sketchy_{sketchy_type}",
                    "category": parts[2] if len(parts) > 2 else None,
                    "sections": parts[3:] if len(parts) > 3 else [],
                    "card_count": count,
                }
        
        return mappings


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse AnKing CrowdAnki export")
    parser.add_argument("export_path", type=Path, help="Path to CrowdAnki JSON export")
    parser.add_argument("--output", type=Path, default=Path("data/anking_tags.json"))
    args = parser.parse_args()
    
    anking_parser = AnKingExportParser()
    anking_parser.parse_export(args.export_path)
    anking_parser.export_tag_mappings(args.output)
    
    print(f"Parsed {len(anking_parser.all_tags)} unique tags")
    print(f"Tag hierarchy saved to {args.output}")
```

### 5.4 MeSH API Client (`scripts/ingest/mesh_api.py`)

```python
"""
MeSH (Medical Subject Headings) API client for medical vocabulary enrichment.

MeSH provides ~30,000 medical terms with hierarchical relationships.
API: https://id.nlm.nih.gov/mesh/
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class MeshConcept:
    """A MeSH concept/descriptor."""
    mesh_id: str
    name: str
    tree_numbers: list[str]
    scope_note: str | None = None
    synonyms: list[str] | None = None
    broader: list[str] | None = None
    narrower: list[str] | None = None


class MeshAPIClient:
    """Client for the NLM MeSH API."""
    
    BASE_URL = "https://id.nlm.nih.gov/mesh"
    
    def __init__(self, cache_dir: Path | None = None):
        self.client = httpx.Client(timeout=30.0)
        self.cache_dir = cache_dir or Path.home() / ".cache" / "medanki" / "mesh"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_concept(self, mesh_id: str) -> MeshConcept | None:
        """Fetch a MeSH concept by ID."""
        cache_path = self.cache_dir / f"{mesh_id}.json"
        
        if cache_path.exists():
            with open(cache_path) as f:
                data = json.load(f)
        else:
            url = f"{self.BASE_URL}/{mesh_id}.json"
            response = self.client.get(url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            with open(cache_path, "w") as f:
                json.dump(data, f)
            
            time.sleep(0.1)  # Rate limiting
        
        return self._parse_concept(data)
    
    def search(self, query: str, limit: int = 20) -> list[MeshConcept]:
        """Search MeSH for concepts matching query."""
        url = f"{self.BASE_URL}/sparql"
        
        sparql_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
        
        SELECT ?d ?label ?treeNumber
        WHERE {{
            ?d a meshv:Descriptor .
            ?d rdfs:label ?label .
            ?d meshv:treeNumber ?treeNumber .
            FILTER(CONTAINS(LCASE(?label), LCASE("{query}")))
        }}
        LIMIT {limit}
        """
        
        response = self.client.get(
            url,
            params={"query": sparql_query, "format": "json"},
        )
        
        if response.status_code != 200:
            return []
        
        results = response.json().get("results", {}).get("bindings", [])
        
        concepts = []
        for result in results:
            mesh_uri = result.get("d", {}).get("value", "")
            mesh_id = mesh_uri.split("/")[-1] if mesh_uri else ""
            
            concepts.append(MeshConcept(
                mesh_id=mesh_id,
                name=result.get("label", {}).get("value", ""),
                tree_numbers=[result.get("treeNumber", {}).get("value", "")],
            ))
        
        return concepts
    
    def _parse_concept(self, data: dict[str, Any]) -> MeshConcept:
        """Parse MeSH JSON-LD response into a concept."""
        return MeshConcept(
            mesh_id=data.get("@id", "").split("/")[-1],
            name=data.get("label", {}).get("@value", ""),
            tree_numbers=self._extract_tree_numbers(data),
            scope_note=data.get("scopeNote", {}).get("@value"),
            synonyms=self._extract_synonyms(data),
            broader=self._extract_relations(data, "broader"),
            narrower=self._extract_relations(data, "narrower"),
        )
    
    def _extract_tree_numbers(self, data: dict) -> list[str]:
        """Extract tree numbers from concept data."""
        tree_nums = data.get("treeNumber", [])
        if isinstance(tree_nums, str):
            return [tree_nums]
        return tree_nums
    
    def _extract_synonyms(self, data: dict) -> list[str]:
        """Extract synonyms/alternative labels."""
        alt_labels = data.get("altLabel", [])
        if isinstance(alt_labels, dict):
            return [alt_labels.get("@value", "")]
        return [l.get("@value", "") for l in alt_labels if isinstance(l, dict)]
    
    def _extract_relations(self, data: dict, relation: str) -> list[str]:
        """Extract related concepts."""
        related = data.get(relation, [])
        if isinstance(related, str):
            return [related.split("/")[-1]]
        return [r.split("/")[-1] for r in related if isinstance(r, str)]
    
    def get_medical_keywords_for_topic(self, topic: str) -> list[str]:
        """Get medical keywords for a given topic using MeSH."""
        concepts = self.search(topic, limit=10)
        
        keywords = set()
        for concept in concepts:
            keywords.add(concept.name.lower())
            if concept.synonyms:
                keywords.update(s.lower() for s in concept.synonyms)
        
        return sorted(keywords)
    
    def build_medical_vocabulary(
        self,
        output_path: Path,
        categories: list[str] | None = None,
    ) -> int:
        """
        Build a local medical vocabulary from MeSH.
        
        Categories are MeSH tree roots like:
        - C: Diseases
        - D: Chemicals and Drugs
        - E: Analytical, Diagnostic and Therapeutic Techniques
        - F: Psychiatry and Psychology
        - G: Phenomena and Processes
        """
        if categories is None:
            categories = ["C", "D", "E", "F", "G"]
        
        vocabulary = {}
        
        for category in categories:
            # This would require paginated SPARQL queries
            # Simplified for demonstration
            pass
        
        with open(output_path, "w") as f:
            json.dump(vocabulary, f, indent=2)
        
        return len(vocabulary)
```

### 5.5 Main Build Script (`scripts/build_taxonomy_db.py`)

```python
"""
Build the taxonomy SQLite database from JSON files and external sources.

Usage:
    python scripts/build_taxonomy_db.py --config config/taxonomy.yaml
    python scripts/build_taxonomy_db.py --mcat-only
    python scripts/build_taxonomy_db.py --enrich-keywords
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class TaxonomyDatabaseBuilder:
    """Build and populate the taxonomy SQLite database."""
    
    def __init__(self, db_path: Path, schema_path: Path):
        self.db_path = db_path
        self.schema_path = schema_path
        self.conn: sqlite3.Connection | None = None
    
    def connect(self) -> None:
        """Connect to database and create schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Execute schema
        with open(self.schema_path) as f:
            self.conn.executescript(f.read())
        
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def load_mcat_taxonomy(self, json_path: Path) -> int:
        """Load MCAT taxonomy from JSON file."""
        with open(json_path) as f:
            data = json.load(f)
        
        exam_id = data["exam"]
        
        # Insert exam
        self.conn.execute(
            """
            INSERT OR REPLACE INTO exams (id, name, description, version, source_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                exam_id,
                "MCAT",
                "Medical College Admission Test",
                data.get("version", "2024"),
                data.get("source_url"),
            ),
        )
        
        node_count = 0
        
        # Process sections
        for section in data.get("sections", []):
            section_id = f"MCAT::{section['id']}"
            
            self._insert_node(
                node_id=section_id,
                exam_id=exam_id,
                node_type="section",
                code=section["code"],
                title=section["title"],
                metadata=json.dumps({
                    "questions": section.get("questions"),
                    "time_minutes": section.get("time_minutes"),
                    "discipline_breakdown": section.get("discipline_breakdown"),
                }),
            )
            node_count += 1
            
            # Process foundational concepts
            for fc in section.get("foundational_concepts", []):
                fc_id = f"MCAT::{fc['id']}"
                
                self._insert_node(
                    node_id=fc_id,
                    exam_id=exam_id,
                    node_type="foundational_concept",
                    code=fc["code"],
                    title=fc["title"],
                    percentage=fc.get("percentage"),
                )
                node_count += 1
                
                # Insert edge to section
                self._insert_edge(section_id, fc_id, depth=1)
                
                # Insert FC keywords
                for kw in fc.get("keywords", []):
                    self._insert_keyword(fc_id, kw)
                
                # Process categories
                for cat in fc.get("categories", []):
                    cat_id = f"MCAT::{cat['id']}"
                    
                    self._insert_node(
                        node_id=cat_id,
                        exam_id=exam_id,
                        node_type="content_category",
                        code=cat["code"],
                        title=cat["title"],
                        metadata=json.dumps({"discipline": cat.get("discipline")}),
                    )
                    node_count += 1
                    
                    # Insert edges
                    self._insert_edge(section_id, cat_id, depth=2)
                    self._insert_edge(fc_id, cat_id, depth=1)
                    
                    # Process topics
                    for topic in cat.get("topics", []):
                        topic_id = f"MCAT::{topic['id']}"
                        
                        self._insert_node(
                            node_id=topic_id,
                            exam_id=exam_id,
                            node_type="topic",
                            code=topic["id"],
                            title=topic["title"],
                            metadata=json.dumps({
                                "subtopics": topic.get("subtopics"),
                                "formulas": topic.get("formulas"),
                                "researchers": topic.get("researchers"),
                            }),
                        )
                        node_count += 1
                        
                        # Insert edges
                        self._insert_edge(cat_id, topic_id, depth=1)
                        self._insert_edge(fc_id, topic_id, depth=2)
                        self._insert_edge(section_id, topic_id, depth=3)
                        
                        # Insert keywords
                        for kw in topic.get("keywords", []):
                            self._insert_keyword(topic_id, kw)
        
        self.conn.commit()
        return node_count
    
    def load_usmle_taxonomy(self, json_path: Path) -> int:
        """Load USMLE Step 1 taxonomy from JSON file."""
        with open(json_path) as f:
            data = json.load(f)
        
        exam_id = data["exam"]
        
        # Insert exam
        self.conn.execute(
            """
            INSERT OR REPLACE INTO exams (id, name, description, version, source_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                exam_id,
                "USMLE Step 1",
                "United States Medical Licensing Examination Step 1",
                data.get("version", "2024"),
                data.get("source_url"),
            ),
        )
        
        node_count = 0
        
        # Process organ systems
        for system in data.get("organ_systems", []):
            system_id = f"Step1::{system['id']}"
            
            self._insert_node(
                node_id=system_id,
                exam_id=exam_id,
                node_type="organ_system",
                code=system["code"],
                title=system["title"],
                metadata=json.dumps({
                    "nbme_chapter": system.get("nbme_chapter"),
                    "first_aid_chapter": system.get("first_aid_chapter"),
                    "pathoma_chapters": system.get("pathoma_chapters"),
                }),
            )
            node_count += 1
            
            # Insert keywords
            for kw in system.get("keywords", []):
                self._insert_keyword(system_id, kw)
            
            # Process topics (grouped by discipline)
            for topic_group in system.get("topics", []):
                topic_id = f"Step1::{topic_group['id']}"
                discipline = topic_group.get("discipline", "General")
                
                self._insert_node(
                    node_id=topic_id,
                    exam_id=exam_id,
                    node_type="topic",
                    code=topic_group["id"],
                    title=topic_group["title"],
                    metadata=json.dumps({"discipline": discipline}),
                )
                node_count += 1
                
                self._insert_edge(system_id, topic_id, depth=1)
                
                # Process subtopics
                for subtopic in topic_group.get("subtopics", []):
                    subtopic_id = f"Step1::{subtopic['id']}"
                    
                    self._insert_node(
                        node_id=subtopic_id,
                        exam_id=exam_id,
                        node_type="subtopic",
                        code=subtopic["id"],
                        title=subtopic["title"],
                        metadata=json.dumps({
                            "first_aid_page": subtopic.get("first_aid_page"),
                            "pathoma_chapter": subtopic.get("pathoma_chapter"),
                            "sketchy_path": subtopic.get("sketchy_path"),
                            "sketchy_pharm": subtopic.get("sketchy_pharm"),
                            "boards_beyond": subtopic.get("boards_beyond"),
                        }),
                    )
                    node_count += 1
                    
                    self._insert_edge(topic_id, subtopic_id, depth=1)
                    self._insert_edge(system_id, subtopic_id, depth=2)
                    
                    for kw in subtopic.get("keywords", []):
                        self._insert_keyword(subtopic_id, kw)
        
        # Process disciplines
        for discipline in data.get("disciplines", []):
            disc_id = f"Step1::Disc::{discipline['id']}"
            
            self._insert_node(
                node_id=disc_id,
                exam_id=exam_id,
                node_type="discipline",
                code=discipline["code"],
                title=discipline["title"],
                percentage=discipline.get("percentage_range", {}).get("min"),
                metadata=json.dumps({
                    "percentage_range": discipline.get("percentage_range"),
                    "resources": discipline.get("resources"),
                }),
            )
            node_count += 1
        
        # Insert cross-classifications (system × discipline mappings)
        for mapping in data.get("cross_mappings", {}).get("system_discipline_examples", []):
            system_code = mapping["system"]
            discipline_code = mapping["discipline"]
            
            system_node_id = f"Step1::{system_code}"
            disc_node_id = f"Step1::Disc::DISC_{discipline_code.upper()}"
            
            self.conn.execute(
                """
                INSERT OR IGNORE INTO cross_classifications 
                (primary_node_id, secondary_node_id, relationship_type, weight)
                VALUES (?, ?, 'system_discipline', 1.0)
                """,
                (system_node_id, disc_node_id),
            )
        
        self.conn.commit()
        return node_count
    
    def _insert_node(
        self,
        node_id: str,
        exam_id: str,
        node_type: str,
        code: str,
        title: str,
        description: str | None = None,
        percentage: float | None = None,
        metadata: str | None = None,
    ) -> None:
        """Insert a taxonomy node."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO taxonomy_nodes 
            (id, exam_id, node_type, code, title, description, percentage_weight, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (node_id, exam_id, node_type, code, title, description, percentage, metadata),
        )
    
    def _insert_edge(
        self,
        ancestor_id: str,
        descendant_id: str,
        depth: int,
    ) -> None:
        """Insert an edge in the closure table."""
        # Self-reference
        self.conn.execute(
            """
            INSERT OR IGNORE INTO taxonomy_edges (ancestor_id, descendant_id, depth)
            VALUES (?, ?, 0)
            """,
            (descendant_id, descendant_id),
        )
        
        # Actual edge
        self.conn.execute(
            """
            INSERT OR IGNORE INTO taxonomy_edges (ancestor_id, descendant_id, depth)
            VALUES (?, ?, ?)
            """,
            (ancestor_id, descendant_id, depth),
        )
    
    def _insert_keyword(
        self,
        node_id: str,
        keyword: str,
        keyword_type: str = "general",
        weight: float = 1.0,
    ) -> None:
        """Insert a keyword for a node."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO keywords (node_id, keyword, keyword_type, weight)
            VALUES (?, ?, ?, ?)
            """,
            (node_id, keyword.lower(), keyword_type, weight),
        )
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM exams")
        stats["exams"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM taxonomy_nodes")
        stats["nodes"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM taxonomy_edges")
        stats["edges"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM keywords")
        stats["keywords"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute(
            "SELECT exam_id, node_type, COUNT(*) FROM taxonomy_nodes GROUP BY exam_id, node_type"
        )
        stats["by_type"] = {f"{row[0]}:{row[1]}": row[2] for row in cursor.fetchall()}
        
        return stats


def main():
    parser = argparse.ArgumentParser(description="Build taxonomy database")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/taxonomy.db"),
        help="Output database path",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=Path("packages/core/src/medanki/storage/taxonomy_schema.sql"),
        help="SQL schema file path",
    )
    parser.add_argument(
        "--mcat-json",
        type=Path,
        default=Path("data/taxonomies/mcat_complete.json"),
        help="MCAT taxonomy JSON",
    )
    parser.add_argument(
        "--usmle-json",
        type=Path,
        default=Path("data/taxonomies/usmle_step1_complete.json"),
        help="USMLE Step 1 taxonomy JSON",
    )
    parser.add_argument("--mcat-only", action="store_true")
    parser.add_argument("--usmle-only", action="store_true")
    args = parser.parse_args()
    
    console.print("[bold blue]Building Taxonomy Database[/bold blue]")
    
    builder = TaxonomyDatabaseBuilder(args.db_path, args.schema_path)
    
    try:
        builder.connect()
        
        if not args.usmle_only and args.mcat_json.exists():
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Loading MCAT taxonomy...", total=None)
                count = builder.load_mcat_taxonomy(args.mcat_json)
                progress.update(task, completed=True)
            console.print(f"  ✓ Loaded {count} MCAT nodes")
        
        if not args.mcat_only and args.usmle_json.exists():
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Loading USMLE Step 1 taxonomy...", total=None)
                count = builder.load_usmle_taxonomy(args.usmle_json)
                progress.update(task, completed=True)
            console.print(f"  ✓ Loaded {count} USMLE nodes")
        
        stats = builder.get_stats()
        console.print("\n[bold green]Database Statistics:[/bold green]")
        console.print(f"  Exams: {stats['exams']}")
        console.print(f"  Nodes: {stats['nodes']}")
        console.print(f"  Edges: {stats['edges']}")
        console.print(f"  Keywords: {stats['keywords']}")
        
        console.print(f"\n[bold]Database saved to: {args.db_path}[/bold]")
        
    finally:
        builder.close()


if __name__ == "__main__":
    main()
```

---

## 6. Enhanced TaxonomyService

### 6.1 Updated Service (`packages/core/src/medanki/services/taxonomy_v2.py`)

```python
"""
Enhanced taxonomy service with full database support.

Provides:
- Hierarchical navigation (ancestors, descendants)
- Multi-dimensional queries (system × discipline)
- Resource mapping lookups
- Semantic search via Weaviate integration
- AnKing tag generation
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

from ..models.taxonomy import (
    CrossClassification,
    ExamType,
    Keyword,
    NodeType,
    ResourceMapping,
    TaxonomyNode,
)


class TaxonomyServiceV2:
    """Enhanced taxonomy service with SQLite backend."""
    
    def __init__(
        self,
        db_path: Path,
        vector_store: Any | None = None,  # WeaviateStore
    ):
        self.db_path = db_path
        self.vector_store = vector_store
        self._conn: sqlite3.Connection | None = None
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection (lazy initialization)."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # -------------------------------------------------------------------------
    # Core CRUD Operations
    # -------------------------------------------------------------------------
    
    def get_node(self, node_id: str) -> TaxonomyNode | None:
        """Get a single taxonomy node by ID."""
        cursor = self.conn.execute(
            """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE n.id = ?
            GROUP BY n.id
            """,
            (node_id,),
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_node(row)
    
    def get_nodes_by_exam(
        self,
        exam_type: ExamType,
        node_type: NodeType | None = None,
    ) -> list[TaxonomyNode]:
        """Get all nodes for an exam, optionally filtered by type."""
        query = """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE n.exam_id = ?
        """
        params: list[Any] = [exam_type.value]
        
        if node_type:
            query += " AND n.node_type = ?"
            params.append(node_type.value)
        
        query += " GROUP BY n.id ORDER BY n.sort_order"
        
        cursor = self.conn.execute(query, params)
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def get_root_nodes(self, exam_type: ExamType) -> list[TaxonomyNode]:
        """Get top-level nodes (no parents) for an exam."""
        cursor = self.conn.execute(
            """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE n.exam_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM taxonomy_edges e
                WHERE e.descendant_id = n.id AND e.depth > 0
            )
            GROUP BY n.id
            ORDER BY n.sort_order
            """,
            (exam_type.value,),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    # -------------------------------------------------------------------------
    # Hierarchy Navigation
    # -------------------------------------------------------------------------
    
    def get_ancestors(self, node_id: str) -> list[TaxonomyNode]:
        """Get all ancestor nodes (parents, grandparents, etc.)."""
        cursor = self.conn.execute(
            """
            SELECT n.*, e.depth, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            JOIN taxonomy_edges e ON e.ancestor_id = n.id
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE e.descendant_id = ? AND e.depth > 0
            GROUP BY n.id
            ORDER BY e.depth DESC
            """,
            (node_id,),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def get_descendants(
        self,
        node_id: str,
        max_depth: int | None = None,
    ) -> list[TaxonomyNode]:
        """Get all descendant nodes."""
        query = """
            SELECT n.*, e.depth, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            JOIN taxonomy_edges e ON e.descendant_id = n.id
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE e.ancestor_id = ? AND e.depth > 0
        """
        params: list[Any] = [node_id]
        
        if max_depth:
            query += " AND e.depth <= ?"
            params.append(max_depth)
        
        query += " GROUP BY n.id ORDER BY e.depth, n.sort_order"
        
        cursor = self.conn.execute(query, params)
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def get_children(self, node_id: str) -> list[TaxonomyNode]:
        """Get direct children only."""
        return [n for n in self.get_descendants(node_id, max_depth=1)]
    
    def get_path(self, node_id: str) -> str:
        """Get the full path string for a node."""
        ancestors = self.get_ancestors(node_id)
        node = self.get_node(node_id)
        
        if not node:
            return ""
        
        path_parts = [a.title for a in ancestors] + [node.title]
        return " > ".join(path_parts)
    
    # -------------------------------------------------------------------------
    # Search Operations
    # -------------------------------------------------------------------------
    
    def search_by_keyword(
        self,
        keyword: str,
        exam_type: ExamType | None = None,
        limit: int = 20,
    ) -> list[TaxonomyNode]:
        """Search nodes by keyword."""
        query = """
            SELECT DISTINCT n.*, GROUP_CONCAT(k2.keyword, '|') as keywords
            FROM taxonomy_nodes n
            JOIN keywords k ON k.node_id = n.id
            LEFT JOIN keywords k2 ON k2.node_id = n.id
            WHERE k.keyword LIKE ?
        """
        params: list[Any] = [f"%{keyword.lower()}%"]
        
        if exam_type:
            query += " AND n.exam_id = ?"
            params.append(exam_type.value)
        
        query += f" GROUP BY n.id LIMIT {limit}"
        
        cursor = self.conn.execute(query, params)
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def search_by_title(
        self,
        query: str,
        exam_type: ExamType | None = None,
        limit: int = 20,
    ) -> list[TaxonomyNode]:
        """Search nodes by title substring."""
        sql = """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE n.title LIKE ?
        """
        params: list[Any] = [f"%{query}%"]
        
        if exam_type:
            sql += " AND n.exam_id = ?"
            params.append(exam_type.value)
        
        sql += f" GROUP BY n.id LIMIT {limit}"
        
        cursor = self.conn.execute(sql, params)
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    async def semantic_search(
        self,
        query: str,
        exam_type: ExamType | None = None,
        limit: int = 10,
        alpha: float = 0.5,
    ) -> list[tuple[TaxonomyNode, float]]:
        """
        Semantic search using vector store (hybrid search).
        
        Returns list of (node, score) tuples.
        """
        if not self.vector_store:
            raise RuntimeError("Vector store not configured for semantic search")
        
        filters = {}
        if exam_type:
            filters["exam_id"] = exam_type.value
        
        results = await self.vector_store.hybrid_search(
            query=query,
            alpha=alpha,
            limit=limit,
            filters=filters,
        )
        
        nodes_with_scores = []
        for result in results:
            node = self.get_node(result["node_id"])
            if node:
                nodes_with_scores.append((node, result["score"]))
        
        return nodes_with_scores
    
    # -------------------------------------------------------------------------
    # Cross-Classification (USMLE System × Discipline)
    # -------------------------------------------------------------------------
    
    def get_cross_classifications(
        self,
        node_id: str,
        relationship_type: str = "system_discipline",
    ) -> list[TaxonomyNode]:
        """Get nodes in the other dimension of a cross-classification."""
        cursor = self.conn.execute(
            """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            JOIN cross_classifications cc ON (
                (cc.primary_node_id = ? AND cc.secondary_node_id = n.id)
                OR (cc.secondary_node_id = ? AND cc.primary_node_id = n.id)
            )
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE cc.relationship_type = ?
            GROUP BY n.id
            """,
            (node_id, node_id, relationship_type),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    def get_topics_by_system_and_discipline(
        self,
        system_id: str,
        discipline_id: str,
    ) -> list[TaxonomyNode]:
        """
        Get topics at the intersection of a system and discipline.
        
        Example: Get all Cardiology + Pathology topics
        """
        cursor = self.conn.execute(
            """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM taxonomy_nodes n
            JOIN taxonomy_edges e1 ON e1.descendant_id = n.id AND e1.ancestor_id = ?
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE n.node_type IN ('topic', 'subtopic')
            AND json_extract(n.metadata, '$.discipline') = (
                SELECT code FROM taxonomy_nodes WHERE id = ?
            )
            GROUP BY n.id
            ORDER BY n.sort_order
            """,
            (system_id, discipline_id),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    # -------------------------------------------------------------------------
    # Resource Mappings
    # -------------------------------------------------------------------------
    
    def get_resources_for_node(self, node_id: str) -> list[dict]:
        """Get all resource mappings for a taxonomy node."""
        cursor = self.conn.execute(
            """
            SELECT rs.*, r.name as resource_name, r.resource_type,
                   rm.relevance_score, rm.is_primary
            FROM resource_mappings rm
            JOIN resource_sections rs ON rs.id = rm.section_id
            JOIN resources r ON r.id = rs.resource_id
            WHERE rm.node_id = ?
            ORDER BY rm.is_primary DESC, rm.relevance_score DESC
            """,
            (node_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_first_aid_page(self, node_id: str) -> int | None:
        """Get First Aid page number for a node."""
        node = self.get_node(node_id)
        if node and node.metadata:
            return node.metadata.get("first_aid_page")
        return None
    
    # -------------------------------------------------------------------------
    # AnKing Tag Generation
    # -------------------------------------------------------------------------
    
    def generate_anking_tag(self, node_id: str) -> str:
        """
        Generate AnKing-compatible tag for a node.
        
        Format: #AK_Step1_v12::#Resource::Chapter::Section
        """
        node = self.get_node(node_id)
        if not node:
            return ""
        
        ancestors = self.get_ancestors(node_id)
        
        # Determine exam prefix
        if node.exam_type == ExamType.MCAT:
            prefix = "#AK_MCAT"
        else:
            prefix = "#AK_Step1_v12"
        
        # Build path
        path_parts = [a.code or a.title.replace(" ", "_") for a in ancestors]
        path_parts.append(node.code or node.title.replace(" ", "_"))
        
        # Clean parts (no spaces, special chars)
        clean_parts = []
        for part in path_parts:
            clean = part.replace(" ", "_").replace("/", "_").replace("&", "and")
            clean_parts.append(clean)
        
        return f"{prefix}::" + "::".join(clean_parts)
    
    def get_nodes_for_anking_tag(self, tag: str) -> list[TaxonomyNode]:
        """Find taxonomy nodes matching an AnKing tag pattern."""
        cursor = self.conn.execute(
            """
            SELECT n.*, GROUP_CONCAT(k.keyword, '|') as keywords
            FROM anking_tags at
            JOIN taxonomy_nodes n ON n.id = at.node_id
            LEFT JOIN keywords k ON k.node_id = n.id
            WHERE at.tag_path LIKE ?
            GROUP BY n.id
            """,
            (f"{tag}%",),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def _row_to_node(self, row: sqlite3.Row) -> TaxonomyNode:
        """Convert a database row to a TaxonomyNode."""
        keywords_str = row["keywords"] or ""
        keywords = [
            Keyword(text=kw.strip())
            for kw in keywords_str.split("|")
            if kw.strip()
        ]
        
        metadata = {}
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError:
                pass
        
        return TaxonomyNode(
            id=row["id"],
            exam_type=ExamType(row["exam_id"]),
            node_type=NodeType(row["node_type"]),
            code=row["code"],
            title=row["title"],
            description=row.get("description"),
            keywords=keywords,
            percentage_weight=row.get("percentage_weight"),
            metadata=metadata,
            depth=row.get("depth", 0),
        )
    
    def get_statistics(self) -> dict:
        """Get taxonomy database statistics."""
        stats = {}
        
        cursor = self.conn.execute(
            "SELECT exam_id, COUNT(*) FROM taxonomy_nodes GROUP BY exam_id"
        )
        stats["nodes_by_exam"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor = self.conn.execute(
            "SELECT node_type, COUNT(*) FROM taxonomy_nodes GROUP BY node_type"
        )
        stats["nodes_by_type"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM keywords")
        stats["total_keywords"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM resource_mappings")
        stats["resource_mappings"] = cursor.fetchone()[0]
        
        return stats
```

---

## 7. External Data Source Integration

### 7.1 Integration Overview

| Source | Data Type | Integration Method | Priority |
|--------|-----------|-------------------|----------|
| **Hugging Face** | Q&A pairs, keywords | Python `datasets` library | High |
| **AnKing Export** | Tag hierarchy, card counts | CrowdAnki JSON parsing | High |
| **MeSH API** | Medical vocabulary | REST API calls | Medium |
| **UMLS** | Cross-vocabulary mappings | Local file (license required) | Low |
| **First Aid PDF** | Page mappings | PDF parsing (future) | Low |

### 7.2 Makefile Targets

```makefile
# Add to existing Makefile

# ============================================================================
# Taxonomy Database Targets
# ============================================================================

.PHONY: taxonomy-init taxonomy-build taxonomy-enrich taxonomy-sync taxonomy-validate

TAXONOMY_DB := data/taxonomy.db
TAXONOMY_SCHEMA := packages/core/src/medanki/storage/taxonomy_schema.sql
MCAT_JSON := data/taxonomies/mcat_complete.json
USMLE_JSON := data/taxonomies/usmle_step1_complete.json

## Initialize taxonomy database schema
taxonomy-init:
	@echo "Creating taxonomy database..."
	sqlite3 $(TAXONOMY_DB) < $(TAXONOMY_SCHEMA)
	@echo "Database initialized at $(TAXONOMY_DB)"

## Build taxonomy database from JSON files
taxonomy-build: taxonomy-init
	@echo "Loading taxonomy data..."
	python scripts/build_taxonomy_db.py \
		--db-path $(TAXONOMY_DB) \
		--schema-path $(TAXONOMY_SCHEMA) \
		--mcat-json $(MCAT_JSON) \
		--usmle-json $(USMLE_JSON)

## Enrich taxonomy with external data (Hugging Face, MeSH)
taxonomy-enrich:
	@echo "Enriching taxonomy with Hugging Face data..."
	python scripts/ingest/huggingface.py --output data/hf_medical_qa.jsonl
	@echo "Enriching taxonomy with MeSH vocabulary..."
	python scripts/ingest/mesh_api.py --output data/mesh_vocabulary.json
	@echo "Updating keyword weights..."
	python scripts/enrich_keywords.py --db-path $(TAXONOMY_DB)

## Sync taxonomy to Weaviate vector store
taxonomy-sync:
	@echo "Syncing taxonomy to Weaviate..."
	python scripts/sync_weaviate.py --db-path $(TAXONOMY_DB)

## Validate taxonomy data
taxonomy-validate:
	@echo "Validating taxonomy..."
	python scripts/validate_taxonomy.py --db-path $(TAXONOMY_DB)

## Full taxonomy pipeline
taxonomy-all: taxonomy-build taxonomy-enrich taxonomy-sync taxonomy-validate
	@echo "Taxonomy pipeline complete!"

## Parse AnKing export (requires manual CrowdAnki export first)
taxonomy-anking:
	@echo "Parsing AnKing export..."
	python scripts/ingest/anking_export.py \
		data/anking_export.json \
		--output data/anking_tags.json
```

---

## 8. Implementation Phases

### Phase 1: Database Foundation (Week 1)

**Deliverables:**
1. `taxonomy_schema.sql` - Complete SQLite schema
2. `models/taxonomy.py` - Pydantic models
3. `build_taxonomy_db.py` - Database build script
4. Complete `mcat_complete.json` with all 10 FCs

**Tasks:**
- [ ] Create SQLite schema with closure table
- [ ] Write Pydantic models for taxonomy entities
- [ ] Implement database builder script
- [ ] Expand MCAT JSON with full topic/subtopic coverage
- [ ] Add Psych/Soc researchers list

### Phase 2: USMLE Taxonomy (Week 2)

**Deliverables:**
1. Complete `usmle_step1_complete.json`
2. All 18 organ systems with topics
3. Cross-classification schema (system × discipline)

**Tasks:**
- [ ] Parse USMLE Content Outline PDF
- [ ] Create all organ system entries
- [ ] Add discipline classifications
- [ ] Implement cross-classification mappings
- [ ] Add First Aid page references

### Phase 3: External Data Integration (Week 3)

**Deliverables:**
1. `huggingface.py` - Dataset ingestion
2. `anking_export.py` - Tag parser
3. `mesh_api.py` - Vocabulary client
4. Enriched keyword database

**Tasks:**
- [ ] Implement Hugging Face dataset loader
- [ ] Parse sample AnKing CrowdAnki export
- [ ] Integrate MeSH API for keyword enrichment
- [ ] Add researcher names to Psych/Soc topics
- [ ] Generate keyword weights from Q&A frequency

### Phase 4: Enhanced TaxonomyService (Week 4)

**Deliverables:**
1. `taxonomy_v2.py` - Full service implementation
2. Weaviate sync script
3. Updated ClassificationService integration
4. AnKing tag generation

**Tasks:**
- [ ] Implement TaxonomyServiceV2 with SQLite backend
- [ ] Add semantic search via Weaviate
- [ ] Implement AnKing tag generation
- [ ] Update ClassificationService to use new taxonomy
- [ ] Add resource mapping queries

### Phase 5: Testing & Documentation (Week 5)

**Deliverables:**
1. Unit tests for all taxonomy components
2. Integration tests with sample data
3. Updated documentation
4. CLI commands for taxonomy management

**Tasks:**
- [ ] Write unit tests for TaxonomyServiceV2
- [ ] Create integration test fixtures
- [ ] Update docs/taxonomy.md
- [ ] Add CLI commands: `medanki taxonomy list`, `medanki taxonomy search`
- [ ] Performance benchmarks

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/unit/test_taxonomy_service.py

import pytest
from pathlib import Path

from medanki.services.taxonomy_v2 import TaxonomyServiceV2
from medanki.models.taxonomy import ExamType, NodeType


@pytest.fixture
def taxonomy_service(tmp_path: Path) -> TaxonomyServiceV2:
    """Create a taxonomy service with test database."""
    db_path = tmp_path / "test_taxonomy.db"
    # Initialize with test data
    return TaxonomyServiceV2(db_path)


class TestTaxonomyServiceV2:
    def test_get_node_returns_none_for_missing(self, taxonomy_service):
        result = taxonomy_service.get_node("nonexistent")
        assert result is None
    
    def test_get_mcat_root_nodes(self, taxonomy_service):
        # Load test MCAT data first
        roots = taxonomy_service.get_root_nodes(ExamType.MCAT)
        assert len(roots) >= 3  # At least 3 sections
        assert all(n.node_type == NodeType.SECTION for n in roots)
    
    def test_get_ancestors_returns_path(self, taxonomy_service):
        # Test with a known topic
        ancestors = taxonomy_service.get_ancestors("MCAT::1A_ENZYME")
        assert len(ancestors) >= 2  # FC1 and Section
        assert ancestors[0].node_type == NodeType.SECTION
    
    def test_search_by_keyword(self, taxonomy_service):
        results = taxonomy_service.search_by_keyword("enzyme")
        assert len(results) > 0
        assert any("enzyme" in n.title.lower() for n in results)
    
    def test_generate_anking_tag(self, taxonomy_service):
        tag = taxonomy_service.generate_anking_tag("MCAT::FC1")
        assert tag.startswith("#AK_MCAT::")
        assert "FC1" in tag
    
    def test_cross_classification_usmle(self, taxonomy_service):
        # Test system × discipline query
        topics = taxonomy_service.get_topics_by_system_and_discipline(
            system_id="Step1::CARDIO",
            discipline_id="Step1::Disc::DISC_PATH",
        )
        assert len(topics) > 0
        # All should have Pathology discipline
        for topic in topics:
            assert topic.metadata.get("discipline") in ["Pathology", "PATH"]
```

### 9.2 Integration Tests

```python
# tests/integration/test_taxonomy_pipeline.py

import pytest
from pathlib import Path

from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder
from medanki.services.taxonomy_v2 import TaxonomyServiceV2


@pytest.fixture
def built_database(tmp_path: Path) -> Path:
    """Build a full taxonomy database for integration testing."""
    db_path = tmp_path / "integration_taxonomy.db"
    schema_path = Path("packages/core/src/medanki/storage/taxonomy_schema.sql")
    mcat_path = Path("data/taxonomies/mcat_complete.json")
    
    builder = TaxonomyDatabaseBuilder(db_path, schema_path)
    builder.connect()
    builder.load_mcat_taxonomy(mcat_path)
    builder.close()
    
    return db_path


class TestTaxonomyPipeline:
    def test_full_mcat_hierarchy(self, built_database):
        service = TaxonomyServiceV2(built_database)
        
        # Verify structure
        stats = service.get_statistics()
        assert stats["nodes_by_exam"]["MCAT"] >= 50  # Minimum nodes
        
        # Check hierarchy depth
        fc1 = service.get_node("MCAT::FC1")
        assert fc1 is not None
        
        descendants = service.get_descendants("MCAT::FC1")
        assert len(descendants) >= 4  # Categories
        
        # Check keywords loaded
        assert len(fc1.keywords) >= 3
    
    def test_search_returns_relevant_results(self, built_database):
        service = TaxonomyServiceV2(built_database)
        
        # Search for common MCAT topic
        results = service.search_by_keyword("glycolysis")
        assert len(results) > 0
        
        # Should find metabolism-related topics
        titles = [r.title.lower() for r in results]
        assert any("metabolism" in t or "glycolysis" in t for t in titles)
```

### 9.3 Test Fixtures

```python
# tests/fixtures/taxonomy_fixtures.py

MCAT_MINIMAL = {
    "exam": "MCAT",
    "version": "test",
    "sections": [
        {
            "id": "BIO_BIOCHEM",
            "code": "Section1",
            "title": "Biological and Biochemical Foundations",
            "foundational_concepts": [
                {
                    "id": "FC1",
                    "code": "FC1",
                    "title": "Biomolecules",
                    "percentage": 0.55,
                    "keywords": ["biomolecules", "cells"],
                    "categories": [
                        {
                            "id": "1A",
                            "code": "1A",
                            "title": "Proteins",
                            "topics": [
                                {
                                    "id": "1A_AA",
                                    "title": "Amino Acids",
                                    "keywords": ["amino acid", "zwitterion"],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}

USMLE_MINIMAL = {
    "exam": "USMLE_STEP1",
    "version": "test",
    "organ_systems": [
        {
            "id": "CARDIO",
            "code": "Cardiovascular",
            "title": "Cardiovascular System",
            "keywords": ["heart", "cardiac"],
            "topics": [
                {
                    "id": "CARDIO_PATH",
                    "title": "Cardiac Pathology",
                    "discipline": "Pathology",
                    "subtopics": [
                        {
                            "id": "CARDIO_PATH_CAD",
                            "title": "Coronary Artery Disease",
                            "keywords": ["CAD", "MI", "angina"],
                        }
                    ],
                }
            ],
        }
    ],
    "disciplines": [
        {
            "id": "DISC_PATH",
            "code": "Pathology",
            "title": "Pathology",
        }
    ],
}
```

---

## Summary

This implementation plan provides a comprehensive roadmap for building a robust taxonomy system for MedAnki. Key highlights:

1. **Database Architecture**: SQLite with closure table pattern for efficient hierarchical queries, plus Weaviate for semantic search

2. **Dual Taxonomy Support**: Complete coverage of MCAT (10 FCs, 30+ categories) and USMLE Step 1 (18 systems, 10 disciplines)

3. **External Integration**: Scripts to pull from Hugging Face datasets, AnKing exports, and MeSH vocabulary

4. **Enhanced Service**: Full-featured TaxonomyServiceV2 with semantic search, cross-classification, and AnKing tag generation

5. **Resource Mapping**: Direct links to First Aid pages, Pathoma chapters, Sketchy videos, and Boards & Beyond sections

6. **Testing Strategy**: Comprehensive unit and integration tests with fixtures

The implementation follows your existing project structure and coding patterns, using uv for dependency management and maintaining compatibility with the current `packages/core` architecture.