-- ============================================================================
-- MedAnki Feedback Database Schema
-- Tracks user feedback for quality improvement and classification training
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Card Feedback
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS card_feedback (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down')),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id TEXT NOT NULL REFERENCES card_feedback(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN (
        'inaccurate', 'unclear', 'wrong_answer', 'wrong_topic',
        'too_complex', 'too_simple', 'duplicate'
    )),
    UNIQUE(feedback_id, category)
);

-- ----------------------------------------------------------------------------
-- Taxonomy Corrections
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS taxonomy_corrections (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    original_topic_id TEXT NOT NULL,
    corrected_topic_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Implicit Signals
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS implicit_signals (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    view_time_ms INTEGER DEFAULT 0,
    flip_count INTEGER DEFAULT 0,
    scroll_depth REAL DEFAULT 0.0,
    edit_attempted BOOLEAN DEFAULT FALSE,
    copy_attempted BOOLEAN DEFAULT FALSE,
    skipped BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Feedback Embeddings (for similarity-based quality improvement)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS feedback_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    embedding BLOB NOT NULL,
    is_positive BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, topic_id)
);

-- ----------------------------------------------------------------------------
-- Quality Metrics (daily aggregates)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS quality_metrics_daily (
    date TEXT NOT NULL,
    topic_id TEXT,
    total_cards INTEGER DEFAULT 0,
    thumbs_up_count INTEGER DEFAULT 0,
    thumbs_down_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,
    avg_view_time_ms REAL DEFAULT 0.0,
    PRIMARY KEY (date, topic_id)
);

-- ----------------------------------------------------------------------------
-- Indexes for Performance
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_feedback_card ON card_feedback(card_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON card_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON card_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON card_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_categories_feedback ON feedback_categories(feedback_id);
CREATE INDEX IF NOT EXISTS idx_corrections_card ON taxonomy_corrections(card_id);
CREATE INDEX IF NOT EXISTS idx_corrections_original ON taxonomy_corrections(original_topic_id);
CREATE INDEX IF NOT EXISTS idx_corrections_corrected ON taxonomy_corrections(corrected_topic_id);
CREATE INDEX IF NOT EXISTS idx_signals_card ON implicit_signals(card_id);
CREATE INDEX IF NOT EXISTS idx_signals_user ON implicit_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_card ON feedback_embeddings(card_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_topic ON feedback_embeddings(topic_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_positive ON feedback_embeddings(is_positive);
CREATE INDEX IF NOT EXISTS idx_metrics_date ON quality_metrics_daily(date);
CREATE INDEX IF NOT EXISTS idx_metrics_topic ON quality_metrics_daily(topic_id);
