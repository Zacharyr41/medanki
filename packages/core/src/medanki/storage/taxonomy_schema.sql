-- ============================================================================
-- MedAnki Taxonomy Database Schema
-- Supports hierarchical taxonomies for MCAT and USMLE exams
-- Uses closure table pattern for efficient hierarchy queries
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Core Tables
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS exams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS taxonomy_nodes (
    id TEXT PRIMARY KEY,
    exam_id TEXT NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    node_type TEXT NOT NULL,
    code TEXT,
    title TEXT NOT NULL,
    description TEXT,
    percentage_min REAL,
    percentage_max REAL,
    parent_id TEXT REFERENCES taxonomy_nodes(id) ON DELETE SET NULL,
    sort_order INTEGER DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS taxonomy_edges (
    ancestor_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    descendant_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    depth INTEGER NOT NULL,
    PRIMARY KEY (ancestor_id, descendant_id)
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    keyword_type TEXT DEFAULT 'general',
    weight REAL DEFAULT 1.0,
    source TEXT,
    UNIQUE(node_id, keyword)
);

CREATE TABLE IF NOT EXISTS cross_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    secondary_node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    UNIQUE(primary_node_id, secondary_node_id, relationship_type)
);

-- ----------------------------------------------------------------------------
-- External Resource Integration
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    version TEXT,
    anking_tag_prefix TEXT,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS resource_sections (
    id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    section_type TEXT,
    code TEXT,
    parent_id TEXT REFERENCES resource_sections(id) ON DELETE SET NULL,
    page_start INTEGER,
    page_end INTEGER,
    duration_seconds INTEGER,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS resource_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    section_id TEXT NOT NULL REFERENCES resource_sections(id) ON DELETE CASCADE,
    relevance_score REAL DEFAULT 1.0,
    is_primary BOOLEAN DEFAULT FALSE,
    UNIQUE(node_id, section_id)
);

-- ----------------------------------------------------------------------------
-- MeSH/UMLS Integration
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS mesh_concepts (
    mesh_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tree_numbers JSON,
    scope_note TEXT,
    synonyms JSON,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mesh_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(id) ON DELETE CASCADE,
    mesh_id TEXT NOT NULL REFERENCES mesh_concepts(mesh_id) ON DELETE CASCADE,
    match_score REAL DEFAULT 1.0,
    UNIQUE(node_id, mesh_id)
);

-- ----------------------------------------------------------------------------
-- AnKing Tag Integration
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS anking_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_path TEXT NOT NULL UNIQUE,
    resource TEXT,
    note_count INTEGER DEFAULT 0,
    parent_tag_path TEXT
);

-- ----------------------------------------------------------------------------
-- Indexes for Performance
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_nodes_exam ON taxonomy_nodes(exam_id);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON taxonomy_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON taxonomy_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_edges_ancestor ON taxonomy_edges(ancestor_id);
CREATE INDEX IF NOT EXISTS idx_edges_descendant ON taxonomy_edges(descendant_id);
CREATE INDEX IF NOT EXISTS idx_edges_depth ON taxonomy_edges(depth);
CREATE INDEX IF NOT EXISTS idx_keywords_node ON keywords(node_id);
CREATE INDEX IF NOT EXISTS idx_keywords_text ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_cross_primary ON cross_classifications(primary_node_id);
CREATE INDEX IF NOT EXISTS idx_cross_secondary ON cross_classifications(secondary_node_id);
CREATE INDEX IF NOT EXISTS idx_resource_mappings_node ON resource_mappings(node_id);
CREATE INDEX IF NOT EXISTS idx_anking_tags_resource ON anking_tags(resource);
