"""Tests for taxonomy SQLite schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


class TestSchemaCreation:
    """Tests for taxonomy database schema creation."""

    @pytest.fixture
    def schema_path(self) -> Path:
        return Path("packages/core/src/medanki/storage/taxonomy_schema.sql")

    @pytest.fixture
    def db(self, tmp_path, schema_path) -> sqlite3.Connection:
        db_path = tmp_path / "taxonomy_test.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(schema_path.read_text())
        yield conn
        conn.close()

    def _get_tables(self, conn: sqlite3.Connection) -> list[str]:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row[0] for row in cursor.fetchall()]

    def _get_columns(self, conn: sqlite3.Connection, table: str) -> list[str]:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cursor.fetchall()]

    def _get_indexes(self, conn: sqlite3.Connection) -> list[str]:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        return [row[0] for row in cursor.fetchall()]

    def test_schema_executes_without_errors(self, schema_path, tmp_path):
        """Schema SQL should execute without errors."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_path.read_text())
        conn.close()

    def test_exams_table_exists(self, db):
        """Exams table has correct schema."""
        tables = self._get_tables(db)
        assert "exams" in tables

        columns = self._get_columns(db, "exams")
        assert "id" in columns
        assert "name" in columns
        assert "version" in columns
        assert "source_url" in columns
        assert "created_at" in columns

    def test_taxonomy_nodes_table_exists(self, db):
        """Taxonomy nodes table has correct schema."""
        tables = self._get_tables(db)
        assert "taxonomy_nodes" in tables

        columns = self._get_columns(db, "taxonomy_nodes")
        assert "id" in columns
        assert "exam_id" in columns
        assert "node_type" in columns
        assert "code" in columns
        assert "title" in columns
        assert "description" in columns
        assert "percentage_min" in columns
        assert "percentage_max" in columns
        assert "parent_id" in columns
        assert "sort_order" in columns
        assert "metadata" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_taxonomy_edges_table_exists(self, db):
        """Taxonomy edges (closure table) has correct schema."""
        tables = self._get_tables(db)
        assert "taxonomy_edges" in tables

        columns = self._get_columns(db, "taxonomy_edges")
        assert "ancestor_id" in columns
        assert "descendant_id" in columns
        assert "depth" in columns

    def test_keywords_table_exists(self, db):
        """Keywords table has correct schema."""
        tables = self._get_tables(db)
        assert "keywords" in tables

        columns = self._get_columns(db, "keywords")
        assert "id" in columns
        assert "node_id" in columns
        assert "keyword" in columns
        assert "keyword_type" in columns
        assert "weight" in columns
        assert "source" in columns

    def test_cross_classifications_table_exists(self, db):
        """Cross classifications table has correct schema."""
        tables = self._get_tables(db)
        assert "cross_classifications" in tables

        columns = self._get_columns(db, "cross_classifications")
        assert "id" in columns
        assert "primary_node_id" in columns
        assert "secondary_node_id" in columns
        assert "relationship_type" in columns
        assert "weight" in columns

    def test_resources_table_exists(self, db):
        """Resources table has correct schema."""
        tables = self._get_tables(db)
        assert "resources" in tables

        columns = self._get_columns(db, "resources")
        assert "id" in columns
        assert "name" in columns
        assert "resource_type" in columns
        assert "version" in columns
        assert "anking_tag_prefix" in columns
        assert "metadata" in columns

    def test_resource_sections_table_exists(self, db):
        """Resource sections table has correct schema."""
        tables = self._get_tables(db)
        assert "resource_sections" in tables

        columns = self._get_columns(db, "resource_sections")
        assert "id" in columns
        assert "resource_id" in columns
        assert "title" in columns
        assert "section_type" in columns
        assert "code" in columns
        assert "parent_id" in columns
        assert "page_start" in columns
        assert "page_end" in columns
        assert "duration_seconds" in columns
        assert "sort_order" in columns

    def test_resource_mappings_table_exists(self, db):
        """Resource mappings table has correct schema."""
        tables = self._get_tables(db)
        assert "resource_mappings" in tables

        columns = self._get_columns(db, "resource_mappings")
        assert "id" in columns
        assert "node_id" in columns
        assert "section_id" in columns
        assert "relevance_score" in columns
        assert "is_primary" in columns

    def test_mesh_concepts_table_exists(self, db):
        """MeSH concepts table has correct schema."""
        tables = self._get_tables(db)
        assert "mesh_concepts" in tables

        columns = self._get_columns(db, "mesh_concepts")
        assert "mesh_id" in columns
        assert "name" in columns
        assert "tree_numbers" in columns
        assert "scope_note" in columns
        assert "synonyms" in columns
        assert "fetched_at" in columns

    def test_mesh_mappings_table_exists(self, db):
        """MeSH mappings table has correct schema."""
        tables = self._get_tables(db)
        assert "mesh_mappings" in tables

        columns = self._get_columns(db, "mesh_mappings")
        assert "id" in columns
        assert "node_id" in columns
        assert "mesh_id" in columns
        assert "match_score" in columns

    def test_anking_tags_table_exists(self, db):
        """AnKing tags table has correct schema."""
        tables = self._get_tables(db)
        assert "anking_tags" in tables

        columns = self._get_columns(db, "anking_tags")
        assert "id" in columns
        assert "tag_path" in columns
        assert "resource" in columns
        assert "note_count" in columns
        assert "parent_tag_path" in columns

    def test_indexes_exist(self, db):
        """All required indexes are created."""
        indexes = self._get_indexes(db)

        assert "idx_nodes_exam" in indexes
        assert "idx_nodes_parent" in indexes
        assert "idx_nodes_type" in indexes
        assert "idx_edges_ancestor" in indexes
        assert "idx_edges_descendant" in indexes
        assert "idx_edges_depth" in indexes
        assert "idx_keywords_node" in indexes
        assert "idx_keywords_text" in indexes
        assert "idx_cross_primary" in indexes
        assert "idx_cross_secondary" in indexes
        assert "idx_resource_mappings_node" in indexes
        assert "idx_anking_tags_resource" in indexes


class TestForeignKeys:
    """Tests for foreign key constraints."""

    @pytest.fixture
    def schema_path(self) -> Path:
        return Path("packages/core/src/medanki/storage/taxonomy_schema.sql")

    @pytest.fixture
    def db(self, tmp_path, schema_path) -> sqlite3.Connection:
        db_path = tmp_path / "taxonomy_fk_test.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_path.read_text())
        yield conn
        conn.close()

    def test_taxonomy_nodes_requires_valid_exam(self, db):
        """Taxonomy node must reference valid exam."""
        db.execute("INSERT INTO exams (id, name) VALUES ('MCAT', 'MCAT Exam')")
        db.execute(
            """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title)
               VALUES ('node1', 'MCAT', 'topic', 'Test Topic')"""
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title)
                   VALUES ('node2', 'INVALID', 'topic', 'Invalid')"""
            )

    def test_keywords_requires_valid_node(self, db):
        """Keyword must reference valid taxonomy node."""
        db.execute("INSERT INTO exams (id, name) VALUES ('MCAT', 'MCAT Exam')")
        db.execute(
            """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title)
               VALUES ('node1', 'MCAT', 'topic', 'Test Topic')"""
        )
        db.execute(
            """INSERT INTO keywords (node_id, keyword)
               VALUES ('node1', 'enzyme')"""
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO keywords (node_id, keyword)
                   VALUES ('invalid_node', 'test')"""
            )

    def test_resource_mappings_requires_valid_references(self, db):
        """Resource mapping requires valid node and section."""
        db.execute("INSERT INTO exams (id, name) VALUES ('MCAT', 'MCAT Exam')")
        db.execute(
            """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title)
               VALUES ('node1', 'MCAT', 'topic', 'Test Topic')"""
        )
        db.execute(
            """INSERT INTO resources (id, name, resource_type)
               VALUES ('first_aid', 'First Aid', 'book')"""
        )
        db.execute(
            """INSERT INTO resource_sections (id, resource_id, title)
               VALUES ('fa_ch1', 'first_aid', 'Chapter 1')"""
        )
        db.execute(
            """INSERT INTO resource_mappings (node_id, section_id)
               VALUES ('node1', 'fa_ch1')"""
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO resource_mappings (node_id, section_id)
                   VALUES ('invalid', 'fa_ch1')"""
            )


class TestUniqueConstraints:
    """Tests for unique constraints."""

    @pytest.fixture
    def schema_path(self) -> Path:
        return Path("packages/core/src/medanki/storage/taxonomy_schema.sql")

    @pytest.fixture
    def db(self, tmp_path, schema_path) -> sqlite3.Connection:
        db_path = tmp_path / "taxonomy_unique_test.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(schema_path.read_text())
        yield conn
        conn.close()

    def test_keyword_unique_per_node(self, db):
        """Same keyword can't be added twice to same node."""
        db.execute("INSERT INTO exams (id, name) VALUES ('MCAT', 'MCAT')")
        db.execute(
            """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title)
               VALUES ('node1', 'MCAT', 'topic', 'Test')"""
        )
        db.execute(
            """INSERT INTO keywords (node_id, keyword)
               VALUES ('node1', 'enzyme')"""
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO keywords (node_id, keyword)
                   VALUES ('node1', 'enzyme')"""
            )

    def test_anking_tag_path_unique(self, db):
        """AnKing tag paths must be unique."""
        db.execute(
            """INSERT INTO anking_tags (tag_path, resource)
               VALUES ('#AK_Step1::FirstAid::Ch1', 'FirstAid')"""
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO anking_tags (tag_path, resource)
                   VALUES ('#AK_Step1::FirstAid::Ch1', 'FirstAid')"""
            )

    def test_closure_table_composite_key(self, db):
        """Closure table has composite primary key."""
        db.execute("INSERT INTO exams (id, name) VALUES ('MCAT', 'MCAT')")
        db.execute(
            """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title)
               VALUES ('node1', 'MCAT', 'section', 'Section')"""
        )
        db.execute(
            """INSERT INTO taxonomy_nodes (id, exam_id, node_type, title, parent_id)
               VALUES ('node2', 'MCAT', 'topic', 'Topic', 'node1')"""
        )
        db.execute(
            """INSERT INTO taxonomy_edges (ancestor_id, descendant_id, depth)
               VALUES ('node1', 'node2', 1)"""
        )
        db.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO taxonomy_edges (ancestor_id, descendant_id, depth)
                   VALUES ('node1', 'node2', 1)"""
            )
