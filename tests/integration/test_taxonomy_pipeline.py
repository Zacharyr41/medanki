"""Integration tests for the full taxonomy pipeline.

Tests the complete flow from database building through classification.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from medanki.models.enums import ExamType
from medanki.models.taxonomy import NodeType, TaxonomyNode
from medanki.storage.taxonomy_repository import TaxonomyRepository


@pytest.fixture
def taxonomy_dir() -> Path:
    """Return the path to taxonomy data files."""
    return Path(__file__).parent.parent.parent / "data" / "taxonomies"


@pytest.fixture
async def populated_repo(
    tmp_path: Path, taxonomy_dir: Path
) -> AsyncGenerator[TaxonomyRepository, None]:
    """Create a repository with real MCAT and USMLE data loaded."""
    db_path = tmp_path / "taxonomy_pipeline.db"
    repo = TaxonomyRepository(db_path)
    await repo.initialize()

    mcat_data = json.loads((taxonomy_dir / "mcat.json").read_text())

    await repo.insert_exam(
        {
            "id": "MCAT",
            "name": "Medical College Admission Test",
            "version": mcat_data.get("version", "2024"),
        }
    )

    for fc in mcat_data.get("foundational_concepts", []):
        await repo.insert_node(
            {
                "id": f"MCAT_{fc['id']}",
                "exam_id": "MCAT",
                "node_type": NodeType.FOUNDATIONAL_CONCEPT.value,
                "code": fc["id"],
                "title": fc["title"],
                "sort_order": int(fc["id"].replace("FC", "")),
            }
        )
        for kw in fc.get("keywords", []):
            await repo.insert_keyword(
                {
                    "node_id": f"MCAT_{fc['id']}",
                    "keyword": kw.lower(),
                }
            )

        for idx, cat in enumerate(fc.get("categories", [])):
            await repo.insert_node(
                {
                    "id": f"MCAT_{cat['id']}",
                    "exam_id": "MCAT",
                    "node_type": NodeType.CONTENT_CATEGORY.value,
                    "code": cat["id"],
                    "title": cat["title"],
                    "parent_id": f"MCAT_{fc['id']}",
                    "sort_order": idx + 1,
                }
            )
            for kw in cat.get("keywords", []):
                await repo.insert_keyword(
                    {
                        "node_id": f"MCAT_{cat['id']}",
                        "keyword": kw.lower(),
                    }
                )

    usmle_data = json.loads((taxonomy_dir / "usmle_step1.json").read_text())

    await repo.insert_exam(
        {
            "id": "USMLE_STEP1",
            "name": "USMLE Step 1",
            "version": usmle_data.get("version", "2024"),
        }
    )

    for idx, sys in enumerate(usmle_data.get("systems", [])):
        await repo.insert_node(
            {
                "id": f"USMLE_{sys['id']}",
                "exam_id": "USMLE_STEP1",
                "node_type": NodeType.ORGAN_SYSTEM.value,
                "code": sys["id"],
                "title": sys["title"],
                "sort_order": idx + 1,
            }
        )
        for kw in sys.get("keywords", []):
            await repo.insert_keyword(
                {
                    "node_id": f"USMLE_{sys['id']}",
                    "keyword": kw.lower(),
                }
            )

        for t_idx, topic in enumerate(sys.get("topics", [])):
            await repo.insert_node(
                {
                    "id": f"USMLE_{topic['id']}",
                    "exam_id": "USMLE_STEP1",
                    "node_type": NodeType.TOPIC.value,
                    "code": topic["id"],
                    "title": topic["title"],
                    "parent_id": f"USMLE_{sys['id']}",
                    "sort_order": t_idx + 1,
                }
            )
            for kw in topic.get("keywords", []):
                await repo.insert_keyword(
                    {
                        "node_id": f"USMLE_{topic['id']}",
                        "keyword": kw.lower(),
                    }
                )

    await repo.build_closure_table()

    yield repo
    await repo.close()


class TestDatabasePopulation:
    """Tests for database population from JSON files."""

    @pytest.mark.asyncio
    async def test_mcat_nodes_loaded(self, populated_repo: TaxonomyRepository):
        """All MCAT nodes are loaded correctly."""
        nodes = await populated_repo.list_nodes_by_exam("MCAT")
        assert len(nodes) == 33

    @pytest.mark.asyncio
    async def test_usmle_nodes_loaded(self, populated_repo: TaxonomyRepository):
        """All USMLE nodes are loaded correctly."""
        nodes = await populated_repo.list_nodes_by_exam("USMLE_STEP1")
        assert len(nodes) == 35

    @pytest.mark.asyncio
    async def test_exams_registered(self, populated_repo: TaxonomyRepository):
        """Both exams are registered in database."""
        exams = await populated_repo.list_exams()
        exam_ids = [e["id"] for e in exams]
        assert "MCAT" in exam_ids
        assert "USMLE_STEP1" in exam_ids

    @pytest.mark.asyncio
    async def test_foundational_concepts_count(self, populated_repo: TaxonomyRepository):
        """Correct number of foundational concepts loaded."""
        fcs = await populated_repo.list_nodes_by_type("MCAT", "foundational_concept")
        assert len(fcs) == 10

    @pytest.mark.asyncio
    async def test_content_categories_count(self, populated_repo: TaxonomyRepository):
        """Correct number of content categories loaded."""
        cats = await populated_repo.list_nodes_by_type("MCAT", "content_category")
        assert len(cats) == 23

    @pytest.mark.asyncio
    async def test_organ_systems_count(self, populated_repo: TaxonomyRepository):
        """Correct number of organ systems loaded."""
        systems = await populated_repo.list_nodes_by_type("USMLE_STEP1", "organ_system")
        assert len(systems) == 10


class TestHierarchyQueries:
    """Tests for hierarchy queries using closure table."""

    @pytest.mark.asyncio
    async def test_get_ancestors_for_category(self, populated_repo: TaxonomyRepository):
        """Categories have correct ancestors."""
        ancestors = await populated_repo.get_ancestors("MCAT_1A")
        assert len(ancestors) == 1
        assert ancestors[0]["id"] == "MCAT_FC1"

    @pytest.mark.asyncio
    async def test_get_descendants_for_fc(self, populated_repo: TaxonomyRepository):
        """Foundational concepts have correct descendants."""
        descendants = await populated_repo.get_descendants("MCAT_FC1")
        assert len(descendants) == 4

    @pytest.mark.asyncio
    async def test_get_children_for_fc(self, populated_repo: TaxonomyRepository):
        """Can get direct children of foundational concept."""
        children = await populated_repo.get_children("MCAT_FC1")
        child_ids = [c["id"] for c in children]
        assert "MCAT_1A" in child_ids
        assert "MCAT_1B" in child_ids

    @pytest.mark.asyncio
    async def test_get_path_for_category(self, populated_repo: TaxonomyRepository):
        """Get full path from root to category."""
        path = await populated_repo.get_path("MCAT_1A")
        assert len(path) == 2
        assert "Biomolecules" in path[0]

    @pytest.mark.asyncio
    async def test_usmle_hierarchy(self, populated_repo: TaxonomyRepository):
        """USMLE hierarchy is correct."""
        ancestors = await populated_repo.get_ancestors("USMLE_SYS3A")
        assert len(ancestors) == 1
        assert "SYS3" in ancestors[0]["id"]


class TestKeywordSearch:
    """Tests for keyword-based search."""

    @pytest.mark.asyncio
    async def test_search_finds_mcat_nodes(self, populated_repo: TaxonomyRepository):
        """Keyword search finds MCAT nodes."""
        results = await populated_repo.search_nodes_by_keyword("protein")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_finds_usmle_nodes(self, populated_repo: TaxonomyRepository):
        """Keyword search finds USMLE nodes."""
        results = await populated_repo.search_nodes_by_keyword("heart")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_keywords_stored_lowercase(self, populated_repo: TaxonomyRepository):
        """Keywords are stored as lowercase for consistent matching."""
        results_lower = await populated_repo.search_nodes_by_keyword("dna")
        assert len(results_lower) > 0
        results_upper = await populated_repo.search_nodes_by_keyword("DNA")
        assert len(results_upper) == 0


class TestTaxonomyServiceV2Integration:
    """Integration tests for TaxonomyServiceV2 with populated database."""

    @pytest.fixture
    def taxonomy_service(self, tmp_path: Path, taxonomy_dir: Path):
        """Create TaxonomyServiceV2 with populated database."""
        from medanki.services.taxonomy_v2 import TaxonomyServiceV2

        db_path = tmp_path / "taxonomy_v2.db"

        async def setup():
            repo = TaxonomyRepository(db_path)
            await repo.initialize()

            mcat_data = json.loads((taxonomy_dir / "mcat.json").read_text())

            await repo.insert_exam(
                {
                    "id": "MCAT",
                    "name": "Medical College Admission Test",
                    "version": mcat_data.get("version", "2024"),
                }
            )

            for fc in mcat_data.get("foundational_concepts", []):
                await repo.insert_node(
                    {
                        "id": f"MCAT_{fc['id']}",
                        "exam_id": "MCAT",
                        "node_type": NodeType.FOUNDATIONAL_CONCEPT.value,
                        "code": fc["id"],
                        "title": fc["title"],
                    }
                )
                for kw in fc.get("keywords", []):
                    await repo.insert_keyword(
                        {
                            "node_id": f"MCAT_{fc['id']}",
                            "keyword": kw.lower(),
                        }
                    )

                for cat in fc.get("categories", []):
                    await repo.insert_node(
                        {
                            "id": f"MCAT_{cat['id']}",
                            "exam_id": "MCAT",
                            "node_type": NodeType.CONTENT_CATEGORY.value,
                            "code": cat["id"],
                            "title": cat["title"],
                            "parent_id": f"MCAT_{fc['id']}",
                        }
                    )
                    for kw in cat.get("keywords", []):
                        await repo.insert_keyword(
                            {
                                "node_id": f"MCAT_{cat['id']}",
                                "keyword": kw.lower(),
                            }
                        )

            await repo.build_closure_table()
            await repo.close()

        asyncio.get_event_loop().run_until_complete(setup())
        return TaxonomyServiceV2(db_path)

    @pytest.mark.asyncio
    async def test_get_node_returns_taxonomy_node(self, taxonomy_service):
        """Service returns proper TaxonomyNode instances."""
        node = await taxonomy_service.get_node("MCAT_FC1")
        assert node is not None
        assert isinstance(node, TaxonomyNode)

    @pytest.mark.asyncio
    async def test_get_nodes_by_exam(self, taxonomy_service):
        """Service returns all nodes for an exam."""
        nodes = await taxonomy_service.get_nodes_by_exam(ExamType.MCAT)
        assert len(nodes) == 33

    @pytest.mark.asyncio
    async def test_get_root_nodes(self, taxonomy_service):
        """Service returns root nodes correctly."""
        roots = await taxonomy_service.get_root_nodes(ExamType.MCAT)
        assert len(roots) == 10
        for root in roots:
            assert root.parent_id is None

    @pytest.mark.asyncio
    async def test_get_ancestors(self, taxonomy_service):
        """Service returns ancestors correctly."""
        ancestors = await taxonomy_service.get_ancestors("MCAT_1A")
        assert len(ancestors) == 1
        assert ancestors[0].id == "MCAT_FC1"

    @pytest.mark.asyncio
    async def test_get_descendants(self, taxonomy_service):
        """Service returns descendants correctly."""
        descendants = await taxonomy_service.get_descendants("MCAT_FC1")
        assert len(descendants) == 4

    @pytest.mark.asyncio
    async def test_get_path(self, taxonomy_service):
        """Service generates correct path string."""
        path = await taxonomy_service.get_path("MCAT_1A")
        assert ">" in path
        assert "Biomolecules" in path

    @pytest.mark.asyncio
    async def test_search_by_keyword(self, taxonomy_service):
        """Service search returns matching nodes."""
        results = await taxonomy_service.search_by_keyword("amino")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_generate_anking_tag(self, taxonomy_service):
        """Service generates AnKing-style tags."""
        tag = await taxonomy_service.generate_anking_tag("MCAT_FC1")
        assert "#AK" in tag
        assert "MCAT" in tag

    @pytest.mark.asyncio
    async def test_context_manager(self, taxonomy_service):
        """Service works as async context manager."""
        async with taxonomy_service:
            node = await taxonomy_service.get_node("MCAT_FC1")
            assert node is not None


class TestClassificationWorkflow:
    """Tests for the classification workflow."""

    @pytest.mark.asyncio
    async def test_classify_cardio_content(self, populated_repo: TaxonomyRepository):
        """Can find relevant topics for cardiovascular content."""
        results = await populated_repo.search_nodes_by_keyword("cardiovascular")
        assert len(results) > 0

        usmle_matches = [r for r in results if r["exam_id"] == "USMLE_STEP1"]
        mcat_matches = [r for r in results if r["exam_id"] == "MCAT"]

        assert len(usmle_matches) > 0 or len(mcat_matches) > 0

    @pytest.mark.asyncio
    async def test_classify_biochem_content(self, populated_repo: TaxonomyRepository):
        """Can find relevant topics for biochemistry content."""
        results = await populated_repo.search_nodes_by_keyword("enzymes")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_classify_genetics_content(self, populated_repo: TaxonomyRepository):
        """Can find relevant topics for genetics content."""
        results = await populated_repo.search_nodes_by_keyword("genetics")
        assert len(results) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_nonexistent_node(self, populated_repo: TaxonomyRepository):
        """Gracefully handle nonexistent node."""
        node = await populated_repo.get_node("NONEXISTENT_NODE")
        assert node is None

    @pytest.mark.asyncio
    async def test_empty_keyword_search(self, populated_repo: TaxonomyRepository):
        """Handle search with no matches."""
        results = await populated_repo.search_nodes_by_keyword("xyznonexistent123")
        assert results == []

    @pytest.mark.asyncio
    async def test_root_has_no_ancestors(self, populated_repo: TaxonomyRepository):
        """Root nodes have no ancestors."""
        ancestors = await populated_repo.get_ancestors("MCAT_FC1")
        assert len(ancestors) == 0

    @pytest.mark.asyncio
    async def test_leaf_has_no_descendants(self, populated_repo: TaxonomyRepository):
        """Leaf nodes have no descendants."""
        descendants = await populated_repo.get_descendants("MCAT_1A")
        assert len(descendants) == 0
