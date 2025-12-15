"""Tests for TaxonomyServiceV2 with SQLite backend."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncGenerator

import pytest

from medanki.models.enums import ExamType
from medanki.models.taxonomy import NodeType, TaxonomyNode
from medanki.storage.taxonomy_repository import TaxonomyRepository


@pytest.fixture
async def db_path(tmp_path: Path) -> Path:
    """Return temp database path."""
    return tmp_path / "taxonomy_test.db"


@pytest.fixture
async def repo(db_path: Path) -> AsyncGenerator[TaxonomyRepository, None]:
    """Create initialized repository with test data."""
    r = TaxonomyRepository(db_path)
    await r.initialize()

    await r.insert_exam(
        {"id": "MCAT", "name": "Medical College Admission Test", "version": "2024-2025"}
    )
    await r.insert_exam({"id": "USMLE_STEP1", "name": "USMLE Step 1", "version": "2024"})

    await r.insert_node(
        {
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": NodeType.FOUNDATIONAL_CONCEPT.value,
            "code": "FC1",
            "title": "Biomolecules",
            "description": "Properties and functions of biomolecules",
            "percentage_min": 10,
            "percentage_max": 15,
            "sort_order": 1,
        }
    )
    await r.insert_node(
        {
            "id": "1A",
            "exam_id": "MCAT",
            "node_type": NodeType.CONTENT_CATEGORY.value,
            "code": "1A",
            "title": "Structure and function of proteins",
            "parent_id": "FC1",
            "sort_order": 1,
        }
    )
    await r.insert_node(
        {
            "id": "1A_1",
            "exam_id": "MCAT",
            "node_type": NodeType.TOPIC.value,
            "code": "1A.1",
            "title": "Amino acids",
            "parent_id": "1A",
            "sort_order": 1,
        }
    )
    await r.insert_node(
        {
            "id": "1A_2",
            "exam_id": "MCAT",
            "node_type": NodeType.TOPIC.value,
            "code": "1A.2",
            "title": "Protein structure",
            "parent_id": "1A",
            "sort_order": 2,
        }
    )
    await r.insert_node(
        {
            "id": "FC2",
            "exam_id": "MCAT",
            "node_type": NodeType.FOUNDATIONAL_CONCEPT.value,
            "code": "FC2",
            "title": "Cells",
            "sort_order": 2,
        }
    )

    await r.insert_node(
        {
            "id": "CARDIO",
            "exam_id": "USMLE_STEP1",
            "node_type": NodeType.ORGAN_SYSTEM.value,
            "code": "CARDIO",
            "title": "Cardiovascular System",
            "sort_order": 1,
        }
    )
    await r.insert_node(
        {
            "id": "CARDIO_HF",
            "exam_id": "USMLE_STEP1",
            "node_type": NodeType.TOPIC.value,
            "code": "CARDIO_HF",
            "title": "Heart Failure",
            "parent_id": "CARDIO",
            "sort_order": 1,
        }
    )
    await r.insert_node(
        {
            "id": "PATHOLOGY",
            "exam_id": "USMLE_STEP1",
            "node_type": NodeType.DISCIPLINE.value,
            "code": "PATH",
            "title": "Pathology",
            "sort_order": 1,
        }
    )

    await r.bulk_insert_keywords(
        [
            {"node_id": "FC1", "keyword": "enzyme", "keyword_type": "general"},
            {"node_id": "FC1", "keyword": "protein", "keyword_type": "general"},
            {"node_id": "FC1", "keyword": "amino acid", "keyword_type": "general"},
            {"node_id": "1A", "keyword": "protein", "keyword_type": "general"},
            {"node_id": "1A", "keyword": "amino acid", "keyword_type": "general"},
            {"node_id": "1A_1", "keyword": "amino acid", "keyword_type": "general"},
            {"node_id": "1A_1", "keyword": "glycine", "keyword_type": "example"},
            {"node_id": "CARDIO", "keyword": "heart", "keyword_type": "general"},
            {"node_id": "CARDIO", "keyword": "cardiovascular", "keyword_type": "general"},
            {
                "node_id": "CARDIO_HF",
                "keyword": "CHF",
                "keyword_type": "abbreviation",
                "weight": 2.0,
            },
        ]
    )

    await r.add_cross_classification(
        {
            "primary_node_id": "CARDIO_HF",
            "secondary_node_id": "PATHOLOGY",
            "relationship_type": "system_discipline",
            "weight": 1.0,
        }
    )

    await r.insert_resource(
        {
            "id": "first_aid_2024",
            "name": "First Aid for the USMLE Step 1 2024",
            "resource_type": "book",
            "anking_tag_prefix": "#AK_Step1_v12",
        }
    )
    await r.insert_resource_section(
        {
            "id": "fa_cardio",
            "resource_id": "first_aid_2024",
            "title": "Cardiovascular",
            "section_type": "chapter",
            "page_start": 280,
            "page_end": 320,
        }
    )
    await r.insert_resource_section(
        {
            "id": "fa_cardio_hf",
            "resource_id": "first_aid_2024",
            "title": "Heart Failure",
            "section_type": "section",
            "parent_id": "fa_cardio",
            "page_start": 305,
            "page_end": 310,
        }
    )
    await r.add_resource_mapping(
        {
            "node_id": "CARDIO_HF",
            "section_id": "fa_cardio_hf",
            "is_primary": True,
        }
    )

    await r.build_closure_table()

    yield r
    await r.close()


@pytest.fixture
def taxonomy_service(db_path: Path, repo: TaxonomyRepository):
    """Create TaxonomyServiceV2 instance."""
    from medanki.services.taxonomy_v2 import TaxonomyServiceV2

    return TaxonomyServiceV2(db_path)


class TestGetNode:
    """Tests for get_node method."""

    @pytest.mark.asyncio
    async def test_get_node_returns_taxonomy_node(self, taxonomy_service):
        """Returns TaxonomyNode instance for valid ID."""
        node = await taxonomy_service.get_node("FC1")

        assert node is not None
        assert isinstance(node, TaxonomyNode)
        assert node.id == "FC1"
        assert node.title == "Biomolecules"
        assert node.exam_id == "MCAT"
        assert node.node_type == NodeType.FOUNDATIONAL_CONCEPT

    @pytest.mark.asyncio
    async def test_get_node_returns_none_for_invalid_id(self, taxonomy_service):
        """Returns None for non-existent ID."""
        node = await taxonomy_service.get_node("NONEXISTENT")
        assert node is None

    @pytest.mark.asyncio
    async def test_get_node_includes_keywords(self, taxonomy_service):
        """Node includes associated keywords."""
        node = await taxonomy_service.get_node("FC1")

        assert node is not None
        assert "enzyme" in node.keywords
        assert "protein" in node.keywords


class TestGetNodesByExam:
    """Tests for get_nodes_by_exam method."""

    @pytest.mark.asyncio
    async def test_get_nodes_by_exam_mcat(self, taxonomy_service):
        """Returns all MCAT nodes."""
        nodes = await taxonomy_service.get_nodes_by_exam(ExamType.MCAT)

        assert len(nodes) == 5
        for node in nodes:
            assert node.exam_id == "MCAT"

    @pytest.mark.asyncio
    async def test_get_nodes_by_exam_usmle(self, taxonomy_service):
        """Returns all USMLE nodes."""
        nodes = await taxonomy_service.get_nodes_by_exam(ExamType.USMLE_STEP1)

        assert len(nodes) == 3
        for node in nodes:
            assert node.exam_id == "USMLE_STEP1"

    @pytest.mark.asyncio
    async def test_get_nodes_by_exam_returns_taxonomy_nodes(self, taxonomy_service):
        """Returns list of TaxonomyNode instances."""
        nodes = await taxonomy_service.get_nodes_by_exam(ExamType.MCAT)

        assert all(isinstance(n, TaxonomyNode) for n in nodes)


class TestGetRootNodes:
    """Tests for get_root_nodes method."""

    @pytest.mark.asyncio
    async def test_get_root_nodes_mcat(self, taxonomy_service):
        """Returns root MCAT nodes (foundational concepts)."""
        roots = await taxonomy_service.get_root_nodes(ExamType.MCAT)

        assert len(roots) == 2
        root_ids = [r.id for r in roots]
        assert "FC1" in root_ids
        assert "FC2" in root_ids

    @pytest.mark.asyncio
    async def test_get_root_nodes_have_no_parent(self, taxonomy_service):
        """All root nodes have parent_id = None."""
        roots = await taxonomy_service.get_root_nodes(ExamType.MCAT)

        for root in roots:
            assert root.parent_id is None
            assert root.is_root is True

    @pytest.mark.asyncio
    async def test_get_root_nodes_usmle(self, taxonomy_service):
        """Returns root USMLE nodes (organ systems, disciplines)."""
        roots = await taxonomy_service.get_root_nodes(ExamType.USMLE_STEP1)

        root_ids = [r.id for r in roots]
        assert "CARDIO" in root_ids
        assert "PATHOLOGY" in root_ids


class TestHierarchyGetAncestors:
    """Tests for get_ancestors method using closure table."""

    @pytest.mark.asyncio
    async def test_get_ancestors_returns_all_ancestors(self, taxonomy_service):
        """Returns all ancestors from root to parent."""
        ancestors = await taxonomy_service.get_ancestors("1A_1")

        assert len(ancestors) == 2
        ancestor_ids = [a.id for a in ancestors]
        assert "FC1" in ancestor_ids
        assert "1A" in ancestor_ids

    @pytest.mark.asyncio
    async def test_get_ancestors_ordered_root_to_parent(self, taxonomy_service):
        """Ancestors ordered from root to immediate parent."""
        ancestors = await taxonomy_service.get_ancestors("1A_1")

        assert ancestors[0].id == "FC1"
        assert ancestors[1].id == "1A"

    @pytest.mark.asyncio
    async def test_get_ancestors_empty_for_root(self, taxonomy_service):
        """Root node has no ancestors."""
        ancestors = await taxonomy_service.get_ancestors("FC1")
        assert len(ancestors) == 0


class TestHierarchyGetDescendants:
    """Tests for get_descendants method using closure table."""

    @pytest.mark.asyncio
    async def test_get_descendants_returns_all_descendants(self, taxonomy_service):
        """Returns all descendants at any depth."""
        descendants = await taxonomy_service.get_descendants("FC1")

        assert len(descendants) == 3
        desc_ids = [d.id for d in descendants]
        assert "1A" in desc_ids
        assert "1A_1" in desc_ids
        assert "1A_2" in desc_ids

    @pytest.mark.asyncio
    async def test_get_descendants_with_max_depth(self, taxonomy_service):
        """Respects max_depth parameter."""
        descendants = await taxonomy_service.get_descendants("FC1", max_depth=1)

        assert len(descendants) == 1
        assert descendants[0].id == "1A"

    @pytest.mark.asyncio
    async def test_get_descendants_empty_for_leaf(self, taxonomy_service):
        """Leaf node has no descendants."""
        descendants = await taxonomy_service.get_descendants("1A_1")
        assert len(descendants) == 0


class TestHierarchyGetChildren:
    """Tests for get_children method."""

    @pytest.mark.asyncio
    async def test_get_children_returns_direct_children_only(self, taxonomy_service):
        """Returns only direct children, not grandchildren."""
        children = await taxonomy_service.get_children("FC1")

        assert len(children) == 1
        assert children[0].id == "1A"

    @pytest.mark.asyncio
    async def test_get_children_for_category(self, taxonomy_service):
        """Returns children of content category."""
        children = await taxonomy_service.get_children("1A")

        assert len(children) == 2
        child_ids = [c.id for c in children]
        assert "1A_1" in child_ids
        assert "1A_2" in child_ids


class TestHierarchyGetPath:
    """Tests for get_path method."""

    @pytest.mark.asyncio
    async def test_get_path_returns_hierarchical_string(self, taxonomy_service):
        """Returns path like 'Root > Parent > Node'."""
        path = await taxonomy_service.get_path("1A_1")

        assert path == "Biomolecules > Structure and function of proteins > Amino acids"

    @pytest.mark.asyncio
    async def test_get_path_for_root(self, taxonomy_service):
        """Root node returns just its title."""
        path = await taxonomy_service.get_path("FC1")
        assert path == "Biomolecules"

    @pytest.mark.asyncio
    async def test_get_path_returns_empty_for_invalid_id(self, taxonomy_service):
        """Returns empty string for non-existent node."""
        path = await taxonomy_service.get_path("NONEXISTENT")
        assert path == ""


class TestSearchByKeyword:
    """Tests for search_by_keyword method."""

    @pytest.mark.asyncio
    async def test_search_by_keyword_finds_exact_match(self, taxonomy_service):
        """Finds nodes with exact keyword match."""
        results = await taxonomy_service.search_by_keyword("enzyme")

        assert len(results) >= 1
        result_ids = [r.id for r in results]
        assert "FC1" in result_ids

    @pytest.mark.asyncio
    async def test_search_by_keyword_case_insensitive(self, taxonomy_service):
        """Search is case-insensitive."""
        results_lower = await taxonomy_service.search_by_keyword("enzyme")
        results_upper = await taxonomy_service.search_by_keyword("ENZYME")

        assert len(results_lower) == len(results_upper)

    @pytest.mark.asyncio
    async def test_search_by_keyword_filters_by_exam(self, taxonomy_service):
        """Can filter results by exam type."""
        results = await taxonomy_service.search_by_keyword("protein", exam=ExamType.MCAT)

        for result in results:
            assert result.exam_id == "MCAT"

    @pytest.mark.asyncio
    async def test_search_by_keyword_partial_match_in_title(self, taxonomy_service):
        """Matches keywords in title as well."""
        results = await taxonomy_service.search_by_keyword("heart")

        result_ids = [r.id for r in results]
        assert "CARDIO" in result_ids or "CARDIO_HF" in result_ids


class TestSemanticSearch:
    """Tests for semantic_search method."""

    @pytest.mark.asyncio
    async def test_semantic_search_without_vector_store(self, taxonomy_service):
        """Returns empty list when no vector store configured."""
        results = await taxonomy_service.semantic_search("protein folding")
        assert results == []

    @pytest.mark.asyncio
    async def test_semantic_search_with_vector_store(self, db_path, repo):
        """Returns scored results when vector store available."""
        from medanki.services.taxonomy_v2 import TaxonomyServiceV2

        class MockVectorStore:
            async def search(self, query: str, limit: int = 10):
                return [
                    {"node_id": "FC1", "score": 0.95},
                    {"node_id": "1A", "score": 0.85},
                ]

        service = TaxonomyServiceV2(db_path, vector_store=MockVectorStore())
        results = await service.semantic_search("protein folding", limit=5)

        assert len(results) == 2
        assert results[0][1] == 0.95


class TestCrossClassification:
    """Tests for get_topics_by_system_and_discipline method."""

    @pytest.mark.asyncio
    async def test_get_topics_by_system_and_discipline(self, taxonomy_service):
        """Finds topics at intersection of system and discipline."""
        topics = await taxonomy_service.get_topics_by_system_and_discipline("CARDIO", "PATHOLOGY")

        topic_ids = [t.id for t in topics]
        assert "CARDIO_HF" in topic_ids

    @pytest.mark.asyncio
    async def test_get_topics_by_system_and_discipline_empty(self, taxonomy_service):
        """Returns empty list when no cross-classification exists."""
        topics = await taxonomy_service.get_topics_by_system_and_discipline("FC1", "PATHOLOGY")
        assert topics == []


class TestResources:
    """Tests for get_first_aid_page method."""

    @pytest.mark.asyncio
    async def test_get_first_aid_page_returns_page(self, taxonomy_service):
        """Returns First Aid page number for mapped node."""
        page = await taxonomy_service.get_first_aid_page("CARDIO_HF")
        assert page == 305

    @pytest.mark.asyncio
    async def test_get_first_aid_page_returns_none_for_unmapped(self, taxonomy_service):
        """Returns None for node without First Aid mapping."""
        page = await taxonomy_service.get_first_aid_page("FC1")
        assert page is None


class TestAnkingTags:
    """Tests for generate_anking_tag method."""

    @pytest.mark.asyncio
    async def test_generate_anking_tag_format(self, taxonomy_service):
        """Generates tag in AnKing format."""
        tag = await taxonomy_service.generate_anking_tag("CARDIO_HF")

        assert tag.startswith("#AK_")
        assert "Cardiovascular" in tag or "cardio" in tag.lower()

    @pytest.mark.asyncio
    async def test_generate_anking_tag_includes_hierarchy(self, taxonomy_service):
        """Tag includes hierarchical path."""
        tag = await taxonomy_service.generate_anking_tag("1A_1")

        assert "::" in tag

    @pytest.mark.asyncio
    async def test_generate_anking_tag_mcat_format(self, taxonomy_service):
        """MCAT tags follow MCAT convention."""
        tag = await taxonomy_service.generate_anking_tag("FC1")

        assert "MCAT" in tag or "mcat" in tag.lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    @pytest.mark.asyncio
    async def test_service_is_async(self, taxonomy_service):
        """Service methods are async coroutines."""
        import inspect

        assert inspect.iscoroutinefunction(taxonomy_service.get_node)
        assert inspect.iscoroutinefunction(taxonomy_service.get_nodes_by_exam)

    @pytest.mark.asyncio
    async def test_exam_type_enum_compatibility(self, taxonomy_service):
        """Works with ExamType enum from models.enums."""
        nodes = await taxonomy_service.get_nodes_by_exam(ExamType.MCAT)
        assert len(nodes) > 0


class TestConnectionManagement:
    """Tests for database connection management."""

    @pytest.mark.asyncio
    async def test_service_closes_connection(self, db_path, repo):
        """Service properly closes database connection."""
        from medanki.services.taxonomy_v2 import TaxonomyServiceV2

        service = TaxonomyServiceV2(db_path)
        await service.get_node("FC1")
        await service.close()

    @pytest.mark.asyncio
    async def test_service_context_manager(self, db_path, repo):
        """Service works as async context manager."""
        from medanki.services.taxonomy_v2 import TaxonomyServiceV2

        async with TaxonomyServiceV2(db_path) as service:
            node = await service.get_node("FC1")
            assert node is not None
