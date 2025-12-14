"""Tests for taxonomy repository operations."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from medanki.storage.taxonomy_repository import TaxonomyRepository


class TestRepositoryInitialization:
    """Tests for repository initialization."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        yield r
        asyncio.run(r.close())

    def test_creates_tables_on_init(self, repo):
        """Tables created automatically on initialization."""
        tables = asyncio.run(repo.get_tables())
        assert "exams" in tables
        assert "taxonomy_nodes" in tables
        assert "taxonomy_edges" in tables
        assert "keywords" in tables

    def test_schema_idempotent(self, tmp_path):
        """Calling initialize twice doesn't fail."""
        db_path = tmp_path / "taxonomy.db"
        repo = TaxonomyRepository(db_path)
        asyncio.run(repo.initialize())
        asyncio.run(repo.initialize())
        asyncio.run(repo.close())


class TestExamCRUD:
    """Tests for exam CRUD operations."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        yield r
        asyncio.run(r.close())

    def test_insert_exam(self, repo):
        """Creates exam record."""
        exam_id = asyncio.run(repo.insert_exam({
            "id": "MCAT",
            "name": "Medical College Admission Test",
            "version": "2024-2025",
            "source_url": "https://aamc.org"
        }))
        assert exam_id == "MCAT"

    def test_get_exam(self, repo):
        """Retrieves exam by ID."""
        asyncio.run(repo.insert_exam({
            "id": "USMLE_STEP1",
            "name": "USMLE Step 1",
            "version": "2024"
        }))

        exam = asyncio.run(repo.get_exam("USMLE_STEP1"))
        assert exam is not None
        assert exam["name"] == "USMLE Step 1"
        assert exam["version"] == "2024"

    def test_get_exam_not_found(self, repo):
        """Returns None for nonexistent exam."""
        exam = asyncio.run(repo.get_exam("NONEXISTENT"))
        assert exam is None

    def test_list_exams(self, repo):
        """Lists all exams."""
        asyncio.run(repo.insert_exam({"id": "MCAT", "name": "MCAT"}))
        asyncio.run(repo.insert_exam({"id": "USMLE_STEP1", "name": "USMLE Step 1"}))

        exams = asyncio.run(repo.list_exams())
        assert len(exams) == 2


class TestNodeCRUD:
    """Tests for taxonomy node CRUD operations."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        asyncio.run(r.insert_exam({"id": "MCAT", "name": "MCAT"}))
        yield r
        asyncio.run(r.close())

    def test_insert_node(self, repo):
        """Creates taxonomy node."""
        node_id = asyncio.run(repo.insert_node({
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": "foundational_concept",
            "code": "FC1",
            "title": "Biomolecules"
        }))
        assert node_id == "FC1"

    def test_get_node(self, repo):
        """Retrieves node by ID."""
        asyncio.run(repo.insert_node({
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": "foundational_concept",
            "code": "FC1",
            "title": "Biomolecules",
            "description": "Properties of biomolecules"
        }))

        node = asyncio.run(repo.get_node("FC1"))
        assert node is not None
        assert node["title"] == "Biomolecules"
        assert node["description"] == "Properties of biomolecules"

    def test_get_node_not_found(self, repo):
        """Returns None for nonexistent node."""
        node = asyncio.run(repo.get_node("NONEXISTENT"))
        assert node is None

    def test_update_node(self, repo):
        """Updates node fields."""
        asyncio.run(repo.insert_node({
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": "foundational_concept",
            "code": "FC1",
            "title": "Original Title"
        }))

        success = asyncio.run(repo.update_node("FC1", {
            "title": "Updated Title",
            "description": "New description"
        }))

        assert success
        node = asyncio.run(repo.get_node("FC1"))
        assert node["title"] == "Updated Title"
        assert node["description"] == "New description"

    def test_delete_node(self, repo):
        """Deletes node."""
        asyncio.run(repo.insert_node({
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": "foundational_concept",
            "code": "FC1",
            "title": "To Delete"
        }))

        success = asyncio.run(repo.delete_node("FC1"))
        assert success

        node = asyncio.run(repo.get_node("FC1"))
        assert node is None

    def test_list_nodes_by_exam(self, repo):
        """Filters nodes by exam."""
        asyncio.run(repo.insert_node({
            "id": "FC1", "exam_id": "MCAT", "node_type": "foundational_concept",
            "code": "FC1", "title": "FC1"
        }))
        asyncio.run(repo.insert_node({
            "id": "FC2", "exam_id": "MCAT", "node_type": "foundational_concept",
            "code": "FC2", "title": "FC2"
        }))

        nodes = asyncio.run(repo.list_nodes_by_exam("MCAT"))
        assert len(nodes) == 2

    def test_list_nodes_by_type(self, repo):
        """Filters nodes by type."""
        asyncio.run(repo.insert_node({
            "id": "FC1", "exam_id": "MCAT", "node_type": "foundational_concept",
            "code": "FC1", "title": "FC1"
        }))
        asyncio.run(repo.insert_node({
            "id": "1A", "exam_id": "MCAT", "node_type": "content_category",
            "code": "1A", "title": "Category 1A"
        }))

        nodes = asyncio.run(repo.list_nodes_by_type("MCAT", "foundational_concept"))
        assert len(nodes) == 1
        assert nodes[0]["id"] == "FC1"


class TestClosureTable:
    """Tests for closure table hierarchy operations."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        asyncio.run(r.insert_exam({"id": "MCAT", "name": "MCAT"}))
        yield r
        asyncio.run(r.close())

    def test_build_closure_table_single_node(self, repo):
        """Single node has self-reference edge."""
        asyncio.run(repo.insert_node({
            "id": "ROOT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Root"
        }))

        edge_count = asyncio.run(repo.build_closure_table())
        assert edge_count == 1

    def test_build_closure_table_parent_child(self, repo):
        """Parent-child creates 3 edges: 2 self-refs + 1 relationship."""
        asyncio.run(repo.insert_node({
            "id": "PARENT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Parent"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Child", "parent_id": "PARENT"
        }))

        edge_count = asyncio.run(repo.build_closure_table())
        assert edge_count == 3

    def test_build_closure_table_three_levels(self, repo):
        """Three-level hierarchy creates correct edges."""
        asyncio.run(repo.insert_node({
            "id": "PARENT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Parent"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Child", "parent_id": "PARENT"
        }))
        asyncio.run(repo.insert_node({
            "id": "GRANDCHILD", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Grandchild", "parent_id": "CHILD"
        }))

        edge_count = asyncio.run(repo.build_closure_table())
        assert edge_count == 6

    def test_get_ancestors(self, repo):
        """Get all ancestors of a node."""
        asyncio.run(repo.insert_node({
            "id": "PARENT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Parent"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Child", "parent_id": "PARENT"
        }))
        asyncio.run(repo.insert_node({
            "id": "GRANDCHILD", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Grandchild", "parent_id": "CHILD"
        }))
        asyncio.run(repo.build_closure_table())

        ancestors = asyncio.run(repo.get_ancestors("GRANDCHILD"))
        assert len(ancestors) == 2
        ancestor_ids = [a["id"] for a in ancestors]
        assert "PARENT" in ancestor_ids
        assert "CHILD" in ancestor_ids

    def test_get_ancestors_ordered_by_depth(self, repo):
        """Ancestors returned in order from root to immediate parent."""
        asyncio.run(repo.insert_node({
            "id": "ROOT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Root"
        }))
        asyncio.run(repo.insert_node({
            "id": "MIDDLE", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Middle", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "LEAF", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Leaf", "parent_id": "MIDDLE"
        }))
        asyncio.run(repo.build_closure_table())

        ancestors = asyncio.run(repo.get_ancestors("LEAF"))
        assert ancestors[0]["id"] == "ROOT"
        assert ancestors[1]["id"] == "MIDDLE"

    def test_get_descendants(self, repo):
        """Get all descendants of a node."""
        asyncio.run(repo.insert_node({
            "id": "ROOT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Root"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD1", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Child 1", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD2", "exam_id": "MCAT", "node_type": "topic",
            "code": "T2", "title": "Child 2", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "GRANDCHILD", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Grandchild", "parent_id": "CHILD1"
        }))
        asyncio.run(repo.build_closure_table())

        descendants = asyncio.run(repo.get_descendants("ROOT"))
        assert len(descendants) == 3
        desc_ids = [d["id"] for d in descendants]
        assert "CHILD1" in desc_ids
        assert "CHILD2" in desc_ids
        assert "GRANDCHILD" in desc_ids

    def test_get_descendants_with_max_depth(self, repo):
        """Limit descendants to certain depth."""
        asyncio.run(repo.insert_node({
            "id": "ROOT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Root"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Child", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "GRANDCHILD", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Grandchild", "parent_id": "CHILD"
        }))
        asyncio.run(repo.build_closure_table())

        descendants = asyncio.run(repo.get_descendants("ROOT", max_depth=1))
        assert len(descendants) == 1
        assert descendants[0]["id"] == "CHILD"

    def test_get_children(self, repo):
        """Get direct children only."""
        asyncio.run(repo.insert_node({
            "id": "ROOT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Root"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD1", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Child 1", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD2", "exam_id": "MCAT", "node_type": "topic",
            "code": "T2", "title": "Child 2", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "GRANDCHILD", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Grandchild", "parent_id": "CHILD1"
        }))
        asyncio.run(repo.build_closure_table())

        children = asyncio.run(repo.get_children("ROOT"))
        assert len(children) == 2

    def test_get_path(self, repo):
        """Get full path from root to node."""
        asyncio.run(repo.insert_node({
            "id": "ROOT", "exam_id": "MCAT", "node_type": "section",
            "code": "S1", "title": "Biology"
        }))
        asyncio.run(repo.insert_node({
            "id": "CHILD", "exam_id": "MCAT", "node_type": "topic",
            "code": "T1", "title": "Cell Biology", "parent_id": "ROOT"
        }))
        asyncio.run(repo.insert_node({
            "id": "LEAF", "exam_id": "MCAT", "node_type": "subtopic",
            "code": "ST1", "title": "Mitochondria", "parent_id": "CHILD"
        }))
        asyncio.run(repo.build_closure_table())

        path = asyncio.run(repo.get_path("LEAF"))
        assert path == ["Biology", "Cell Biology", "Mitochondria"]


class TestKeywordOperations:
    """Tests for keyword management."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        asyncio.run(r.insert_exam({"id": "MCAT", "name": "MCAT"}))
        asyncio.run(r.insert_node({
            "id": "FC1", "exam_id": "MCAT", "node_type": "foundational_concept",
            "code": "FC1", "title": "Biomolecules"
        }))
        yield r
        asyncio.run(r.close())

    def test_insert_keyword(self, repo):
        """Creates keyword for node."""
        kw_id = asyncio.run(repo.insert_keyword({
            "node_id": "FC1",
            "keyword": "enzyme",
            "keyword_type": "general"
        }))
        assert kw_id > 0

    def test_insert_keyword_with_weight(self, repo):
        """Creates keyword with weight."""
        kw_id = asyncio.run(repo.insert_keyword({
            "node_id": "FC1",
            "keyword": "ATP",
            "keyword_type": "abbreviation",
            "weight": 2.0
        }))

        keywords = asyncio.run(repo.get_keywords_for_node("FC1"))
        atp_kw = next(k for k in keywords if k["keyword"] == "ATP")
        assert atp_kw["weight"] == 2.0

    def test_get_keywords_for_node(self, repo):
        """Retrieves all keywords for a node."""
        asyncio.run(repo.insert_keyword({"node_id": "FC1", "keyword": "enzyme"}))
        asyncio.run(repo.insert_keyword({"node_id": "FC1", "keyword": "protein"}))
        asyncio.run(repo.insert_keyword({"node_id": "FC1", "keyword": "catalyst"}))

        keywords = asyncio.run(repo.get_keywords_for_node("FC1"))
        assert len(keywords) == 3
        kw_texts = [k["keyword"] for k in keywords]
        assert "enzyme" in kw_texts
        assert "protein" in kw_texts

    def test_bulk_insert_keywords(self, repo):
        """Inserts multiple keywords efficiently."""
        keywords = [
            {"node_id": "FC1", "keyword": "amino acid"},
            {"node_id": "FC1", "keyword": "peptide"},
            {"node_id": "FC1", "keyword": "protein"},
            {"node_id": "FC1", "keyword": "enzyme"},
        ]

        count = asyncio.run(repo.bulk_insert_keywords(keywords))
        assert count == 4

        stored = asyncio.run(repo.get_keywords_for_node("FC1"))
        assert len(stored) == 4

    def test_search_nodes_by_keyword(self, repo):
        """Finds nodes by keyword match."""
        asyncio.run(repo.insert_node({
            "id": "FC2", "exam_id": "MCAT", "node_type": "foundational_concept",
            "code": "FC2", "title": "Cells"
        }))
        asyncio.run(repo.insert_keyword({"node_id": "FC1", "keyword": "enzyme"}))
        asyncio.run(repo.insert_keyword({"node_id": "FC1", "keyword": "protein"}))
        asyncio.run(repo.insert_keyword({"node_id": "FC2", "keyword": "membrane"}))
        asyncio.run(repo.insert_keyword({"node_id": "FC2", "keyword": "protein"}))

        nodes = asyncio.run(repo.search_nodes_by_keyword("protein"))
        assert len(nodes) == 2

        nodes = asyncio.run(repo.search_nodes_by_keyword("enzyme"))
        assert len(nodes) == 1
        assert nodes[0]["id"] == "FC1"


class TestBulkOperations:
    """Tests for bulk insert operations."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        asyncio.run(r.insert_exam({"id": "MCAT", "name": "MCAT"}))
        yield r
        asyncio.run(r.close())

    def test_bulk_insert_nodes(self, repo):
        """Inserts multiple nodes efficiently."""
        nodes = [
            {"id": f"NODE_{i}", "exam_id": "MCAT", "node_type": "topic",
             "code": f"N{i}", "title": f"Node {i}"}
            for i in range(100)
        ]

        count = asyncio.run(repo.bulk_insert_nodes(nodes))
        assert count == 100

        all_nodes = asyncio.run(repo.list_nodes_by_exam("MCAT"))
        assert len(all_nodes) == 100


class TestCrossClassification:
    """Tests for USMLE system × discipline cross-classification."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        asyncio.run(r.insert_exam({"id": "USMLE_STEP1", "name": "USMLE Step 1"}))
        asyncio.run(r.insert_node({
            "id": "CARDIO", "exam_id": "USMLE_STEP1", "node_type": "organ_system",
            "code": "CARDIO", "title": "Cardiovascular"
        }))
        asyncio.run(r.insert_node({
            "id": "PATHOLOGY", "exam_id": "USMLE_STEP1", "node_type": "discipline",
            "code": "PATH", "title": "Pathology"
        }))
        yield r
        asyncio.run(r.close())

    def test_add_cross_classification(self, repo):
        """Creates system-discipline mapping."""
        cc_id = asyncio.run(repo.add_cross_classification({
            "primary_node_id": "CARDIO",
            "secondary_node_id": "PATHOLOGY",
            "relationship_type": "system_discipline"
        }))
        assert cc_id > 0

    def test_get_cross_classifications(self, repo):
        """Retrieves cross-classifications for a node."""
        asyncio.run(repo.add_cross_classification({
            "primary_node_id": "CARDIO",
            "secondary_node_id": "PATHOLOGY",
            "relationship_type": "system_discipline"
        }))

        mappings = asyncio.run(repo.get_cross_classifications("CARDIO"))
        assert len(mappings) == 1
        assert mappings[0]["secondary_node_id"] == "PATHOLOGY"


class TestResourceMappings:
    """Tests for resource section mappings."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        asyncio.run(r.insert_exam({"id": "USMLE_STEP1", "name": "USMLE Step 1"}))
        asyncio.run(r.insert_node({
            "id": "CARDIO", "exam_id": "USMLE_STEP1", "node_type": "organ_system",
            "code": "CARDIO", "title": "Cardiovascular"
        }))
        asyncio.run(r.insert_resource({
            "id": "first_aid", "name": "First Aid", "resource_type": "book"
        }))
        asyncio.run(r.insert_resource_section({
            "id": "fa_cardio", "resource_id": "first_aid", "title": "Cardiovascular"
        }))
        yield r
        asyncio.run(r.close())

    def test_insert_resource(self, repo):
        """Creates resource record."""
        res_id = asyncio.run(repo.insert_resource({
            "id": "pathoma", "name": "Pathoma", "resource_type": "video_series"
        }))
        assert res_id == "pathoma"

    def test_insert_resource_section(self, repo):
        """Creates resource section."""
        section_id = asyncio.run(repo.insert_resource_section({
            "id": "fa_cardio_hf",
            "resource_id": "first_aid",
            "title": "Heart Failure",
            "page_start": 305,
            "page_end": 310
        }))
        assert section_id == "fa_cardio_hf"

    def test_add_resource_mapping(self, repo):
        """Maps node to resource section."""
        mapping_id = asyncio.run(repo.add_resource_mapping({
            "node_id": "CARDIO",
            "section_id": "fa_cardio",
            "is_primary": True
        }))
        assert mapping_id > 0

    def test_get_resources_for_node(self, repo):
        """Gets all resources mapped to a node."""
        asyncio.run(repo.add_resource_mapping({
            "node_id": "CARDIO",
            "section_id": "fa_cardio",
            "is_primary": True
        }))

        resources = asyncio.run(repo.get_resources_for_node("CARDIO"))
        assert len(resources) == 1
        assert resources[0]["section_id"] == "fa_cardio"


class TestAsyncOperations:
    """Tests for async database operations."""

    @pytest.fixture
    def repo(self, tmp_path) -> TaxonomyRepository:
        db_path = tmp_path / "taxonomy.db"
        r = TaxonomyRepository(db_path)
        asyncio.run(r.initialize())
        yield r
        asyncio.run(r.close())

    def test_concurrent_inserts(self, repo):
        """Handles concurrent inserts."""
        asyncio.run(repo.insert_exam({"id": "MCAT", "name": "MCAT"}))

        async def insert_many():
            tasks = [
                repo.insert_node({
                    "id": f"NODE_{i}", "exam_id": "MCAT", "node_type": "topic",
                    "code": f"N{i}", "title": f"Node {i}"
                })
                for i in range(20)
            ]
            await asyncio.gather(*tasks)

        asyncio.run(insert_many())

        nodes = asyncio.run(repo.list_nodes_by_exam("MCAT"))
        assert len(nodes) == 20
