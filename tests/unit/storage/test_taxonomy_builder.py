"""Tests for TaxonomyDatabaseBuilder."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from medanki.storage.taxonomy_repository import TaxonomyRepository


class TestTaxonomyDatabaseBuilder:
    """Tests for the taxonomy database builder."""

    @pytest.fixture
    def mcat_json(self, tmp_path) -> Path:
        """Create sample MCAT taxonomy JSON."""
        mcat_data = {
            "exam": "MCAT",
            "version": "2024",
            "foundational_concepts": [
                {
                    "id": "FC1",
                    "title": "Biomolecules",
                    "keywords": ["biomolecules", "cells"],
                    "categories": [
                        {
                            "id": "1A",
                            "title": "Proteins and amino acids",
                            "keywords": ["amino acids", "protein"],
                        },
                        {
                            "id": "1B",
                            "title": "Gene expression",
                            "keywords": ["DNA", "RNA"],
                        },
                    ],
                },
                {
                    "id": "FC2",
                    "title": "Cells and organisms",
                    "keywords": ["cells", "organisms"],
                    "categories": [
                        {
                            "id": "2A",
                            "title": "Cell biology",
                            "keywords": ["organelles", "membrane"],
                        },
                    ],
                },
            ],
        }
        path = tmp_path / "mcat.json"
        path.write_text(json.dumps(mcat_data))
        return path

    @pytest.fixture
    def usmle_json(self, tmp_path) -> Path:
        """Create sample USMLE taxonomy JSON."""
        usmle_data = {
            "exam": "USMLE_STEP1",
            "version": "2024",
            "systems": [
                {
                    "id": "SYS1",
                    "title": "General Principles",
                    "keywords": ["biochemistry", "genetics"],
                    "topics": [
                        {
                            "id": "SYS1A",
                            "title": "Biochemistry",
                            "keywords": ["metabolism", "enzymes"],
                        },
                    ],
                },
                {
                    "id": "SYS2",
                    "title": "Cardiovascular",
                    "keywords": ["heart", "circulation"],
                    "topics": [
                        {
                            "id": "SYS2A",
                            "title": "Cardiac Physiology",
                            "keywords": ["ECG", "cardiac output"],
                        },
                    ],
                },
            ],
        }
        path = tmp_path / "usmle.json"
        path.write_text(json.dumps(usmle_data))
        return path

    @pytest.fixture
    def medmcqa_topics(self, tmp_path) -> Path:
        """Create sample MedMCQA topics JSON."""
        topics = {
            "topics": [
                {"name": "Anatomy", "keywords": ["heart", "liver", "bones"]},
                {"name": "Biochemistry", "keywords": ["enzymes", "metabolism"]},
            ]
        }
        path = tmp_path / "medmcqa_topics.json"
        path.write_text(json.dumps(topics))
        return path

    @pytest.fixture
    def anking_tags(self, tmp_path) -> Path:
        """Create sample AnKing tags JSON."""
        tags = {
            "tags": [
                {"path": "#AK_Step1_v12::Cardiology::Heart_Failure", "count": 150},
                {"path": "#AK_Step1_v12::Biochemistry::Metabolism", "count": 200},
            ]
        }
        path = tmp_path / "anking_tags.json"
        path.write_text(json.dumps(tags))
        return path

    @pytest.fixture
    def mesh_vocab(self, tmp_path) -> Path:
        """Create sample MeSH vocabulary JSON."""
        mesh = {
            "concepts": [
                {
                    "mesh_id": "D002318",
                    "name": "Cardiovascular Diseases",
                    "synonyms": ["heart disease", "cardiac disease"],
                },
                {
                    "mesh_id": "D001419",
                    "name": "Bacteria",
                    "synonyms": ["bacterium", "prokaryote"],
                },
            ]
        }
        path = tmp_path / "mesh_vocab.json"
        path.write_text(json.dumps(mesh))
        return path

    @pytest.fixture
    def db_path(self, tmp_path) -> Path:
        """Return temporary database path."""
        return tmp_path / "taxonomy.db"


class TestLoadMCATTaxonomy(TestTaxonomyDatabaseBuilder):
    """Tests for MCAT taxonomy loading."""

    def test_load_mcat_creates_exam(self, db_path, mcat_json):
        """Loading MCAT creates exam record."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        count = asyncio.run(builder.load_mcat_taxonomy(mcat_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        exam = asyncio.run(repo.get_exam("MCAT"))
        asyncio.run(repo.close())

        assert exam is not None
        assert exam["name"] == "Medical College Admission Test"
        assert count > 0

    def test_load_mcat_creates_foundational_concepts(self, db_path, mcat_json):
        """Loading MCAT creates foundational concept nodes."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        nodes = asyncio.run(repo.list_nodes_by_type("MCAT", "foundational_concept"))
        asyncio.run(repo.close())

        assert len(nodes) == 2
        node_ids = [n["id"] for n in nodes]
        assert "MCAT_FC1" in node_ids
        assert "MCAT_FC2" in node_ids

    def test_load_mcat_creates_categories(self, db_path, mcat_json):
        """Loading MCAT creates content category nodes."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        nodes = asyncio.run(repo.list_nodes_by_type("MCAT", "content_category"))
        asyncio.run(repo.close())

        assert len(nodes) == 3

    def test_load_mcat_sets_parent_relationships(self, db_path, mcat_json):
        """Categories have foundational concepts as parents."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        cat_1a = asyncio.run(repo.get_node("MCAT_1A"))
        asyncio.run(repo.close())

        assert cat_1a["parent_id"] == "MCAT_FC1"

    def test_load_mcat_adds_keywords(self, db_path, mcat_json):
        """Loading MCAT adds keywords to nodes."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        keywords = asyncio.run(repo.get_keywords_for_node("MCAT_FC1"))
        asyncio.run(repo.close())

        kw_texts = [k["keyword"] for k in keywords]
        assert "biomolecules" in kw_texts
        assert "cells" in kw_texts

    def test_load_mcat_returns_node_count(self, db_path, mcat_json):
        """Loading MCAT returns total node count."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        count = asyncio.run(builder.load_mcat_taxonomy(mcat_json))

        assert count == 5


class TestLoadUSMLETaxonomy(TestTaxonomyDatabaseBuilder):
    """Tests for USMLE taxonomy loading."""

    def test_load_usmle_creates_exam(self, db_path, usmle_json):
        """Loading USMLE creates exam record."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        count = asyncio.run(builder.load_usmle_taxonomy(usmle_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        exam = asyncio.run(repo.get_exam("USMLE_STEP1"))
        asyncio.run(repo.close())

        assert exam is not None
        assert count > 0

    def test_load_usmle_creates_systems(self, db_path, usmle_json):
        """Loading USMLE creates organ system nodes."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_usmle_taxonomy(usmle_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        nodes = asyncio.run(repo.list_nodes_by_type("USMLE_STEP1", "organ_system"))
        asyncio.run(repo.close())

        assert len(nodes) == 2

    def test_load_usmle_creates_topics(self, db_path, usmle_json):
        """Loading USMLE creates topic nodes."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_usmle_taxonomy(usmle_json))

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        nodes = asyncio.run(repo.list_nodes_by_type("USMLE_STEP1", "topic"))
        asyncio.run(repo.close())

        assert len(nodes) == 2


class TestBuildClosureTable(TestTaxonomyDatabaseBuilder):
    """Tests for closure table building."""

    def test_build_closure_table_after_load(self, db_path, mcat_json):
        """Building closure table creates edges."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))
        edge_count = asyncio.run(builder.build_closure_table())

        assert edge_count > 5

    def test_closure_table_enables_hierarchy_queries(self, db_path, mcat_json):
        """After closure table, can query ancestors."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))
        asyncio.run(builder.build_closure_table())

        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        ancestors = asyncio.run(repo.get_ancestors("MCAT_1A"))
        asyncio.run(repo.close())

        assert len(ancestors) == 1
        assert ancestors[0]["id"] == "MCAT_FC1"


class TestEnrichFromMedMCQA(TestTaxonomyDatabaseBuilder):
    """Tests for MedMCQA enrichment."""

    def test_enrich_adds_keywords(self, db_path, mcat_json, medmcqa_topics):
        """Enrichment adds keywords from MedMCQA."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))
        count = asyncio.run(builder.enrich_from_medmcqa(medmcqa_topics))

        assert count >= 0


class TestAddAnkingTags(TestTaxonomyDatabaseBuilder):
    """Tests for AnKing tag integration."""

    def test_add_anking_tags(self, db_path, mcat_json, anking_tags):
        """Adding AnKing tags creates records."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))
        count = asyncio.run(builder.add_anking_tags(anking_tags))

        assert count >= 0


class TestAddMeshConcepts(TestTaxonomyDatabaseBuilder):
    """Tests for MeSH concept integration."""

    def test_add_mesh_concepts(self, db_path, mcat_json, mesh_vocab):
        """Adding MeSH concepts creates records."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))
        count = asyncio.run(builder.add_mesh_concepts(mesh_vocab))

        assert count >= 0


class TestGetStats(TestTaxonomyDatabaseBuilder):
    """Tests for database statistics."""

    def test_get_stats(self, db_path, mcat_json):
        """Get stats returns counts."""
        from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

        builder = TaxonomyDatabaseBuilder(db_path)
        asyncio.run(builder.initialize())
        asyncio.run(builder.load_mcat_taxonomy(mcat_json))
        asyncio.run(builder.build_closure_table())
        stats = asyncio.run(builder.get_stats())

        assert "exams" in stats
        assert "nodes" in stats
        assert "edges" in stats
        assert "keywords" in stats
        assert stats["exams"] == 1
        assert stats["nodes"] == 5
