"""Integration tests for taxonomy data validation.

These tests validate the actual taxonomy JSON files and ensure
they meet expected counts and structure requirements.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medanki.services.taxonomy import ExamType, TaxonomyService

EXPECTED_COUNTS = {
    "mcat_foundational_concepts": 10,
    "mcat_content_categories": 23,
    "usmle_organ_systems": 10,
    "usmle_topics": 25,
}


@pytest.fixture
def taxonomy_dir() -> Path:
    """Return the path to taxonomy data files."""
    return Path(__file__).parent.parent.parent / "data" / "taxonomies"


@pytest.fixture
def taxonomy_service(taxonomy_dir: Path) -> TaxonomyService:
    """Create a taxonomy service instance with real data."""
    return TaxonomyService(taxonomy_dir)


@pytest.fixture
def mcat_json(taxonomy_dir: Path) -> dict:
    """Load MCAT taxonomy JSON data."""
    with open(taxonomy_dir / "mcat.json") as f:
        return json.load(f)


@pytest.fixture
def usmle_json(taxonomy_dir: Path) -> dict:
    """Load USMLE taxonomy JSON data."""
    with open(taxonomy_dir / "usmle_step1.json") as f:
        return json.load(f)


class TestMCATDataCounts:
    """Tests for MCAT taxonomy data counts."""

    def test_mcat_has_10_foundational_concepts(self, taxonomy_service: TaxonomyService):
        """MCAT must have exactly 10 foundational concepts."""
        fcs = taxonomy_service.get_foundational_concepts(ExamType.MCAT)
        assert len(fcs) == EXPECTED_COUNTS["mcat_foundational_concepts"]

    def test_mcat_has_23_content_categories(self, taxonomy_service: TaxonomyService):
        """MCAT must have exactly 23 content categories."""
        categories = taxonomy_service.get_content_categories(ExamType.MCAT)
        assert len(categories) == EXPECTED_COUNTS["mcat_content_categories"]

    def test_mcat_json_structure(self, mcat_json: dict):
        """MCAT JSON has required structure."""
        assert "exam" in mcat_json
        assert "version" in mcat_json
        assert "foundational_concepts" in mcat_json
        assert mcat_json["exam"] == "MCAT"

    def test_mcat_foundational_concepts_structure(self, mcat_json: dict):
        """Each foundational concept has required fields."""
        for fc in mcat_json["foundational_concepts"]:
            assert "id" in fc
            assert "title" in fc
            assert "categories" in fc
            assert fc["id"].startswith("FC")

    def test_mcat_categories_structure(self, mcat_json: dict):
        """Each content category has required fields."""
        for fc in mcat_json["foundational_concepts"]:
            for cat in fc["categories"]:
                assert "id" in cat
                assert "title" in cat
                assert "keywords" in cat

    def test_mcat_all_fcs_have_categories(self, mcat_json: dict):
        """Every foundational concept has at least one category."""
        for fc in mcat_json["foundational_concepts"]:
            assert len(fc["categories"]) >= 1, f"FC {fc['id']} has no categories"

    def test_mcat_fc_ids_are_unique(self, mcat_json: dict):
        """All foundational concept IDs are unique."""
        fc_ids = [fc["id"] for fc in mcat_json["foundational_concepts"]]
        assert len(fc_ids) == len(set(fc_ids))

    def test_mcat_category_ids_are_unique(self, mcat_json: dict):
        """All category IDs are unique across FCs."""
        all_cat_ids = []
        for fc in mcat_json["foundational_concepts"]:
            for cat in fc["categories"]:
                all_cat_ids.append(cat["id"])
        assert len(all_cat_ids) == len(set(all_cat_ids))


class TestUSMLEDataCounts:
    """Tests for USMLE taxonomy data counts."""

    def test_usmle_has_organ_systems(self, taxonomy_service: TaxonomyService):
        """USMLE has expected number of organ systems."""
        topics = taxonomy_service.get_topics_by_exam(ExamType.USMLE_STEP1)
        root_topics = [t for t in topics if t.parent_id is None]
        assert len(root_topics) == EXPECTED_COUNTS["usmle_organ_systems"]

    def test_usmle_json_structure(self, usmle_json: dict):
        """USMLE JSON has required structure."""
        assert "exam" in usmle_json
        assert "version" in usmle_json
        assert "systems" in usmle_json
        assert usmle_json["exam"] == "USMLE_STEP1"

    def test_usmle_systems_structure(self, usmle_json: dict):
        """Each organ system has required fields."""
        for sys in usmle_json["systems"]:
            assert "id" in sys
            assert "title" in sys
            assert "topics" in sys

    def test_usmle_topics_structure(self, usmle_json: dict):
        """Each topic has required fields."""
        for sys in usmle_json["systems"]:
            for topic in sys["topics"]:
                assert "id" in topic
                assert "title" in topic
                assert "keywords" in topic

    def test_usmle_all_systems_have_topics(self, usmle_json: dict):
        """Every organ system has at least one topic."""
        for sys in usmle_json["systems"]:
            assert len(sys["topics"]) >= 1, f"System {sys['id']} has no topics"

    def test_usmle_system_ids_are_unique(self, usmle_json: dict):
        """All organ system IDs are unique."""
        sys_ids = [sys["id"] for sys in usmle_json["systems"]]
        assert len(sys_ids) == len(set(sys_ids))

    def test_usmle_topic_ids_are_unique(self, usmle_json: dict):
        """All topic IDs are unique across systems."""
        all_topic_ids = []
        for sys in usmle_json["systems"]:
            for topic in sys["topics"]:
                all_topic_ids.append(topic["id"])
        assert len(all_topic_ids) == len(set(all_topic_ids))


class TestKeywordValidation:
    """Tests for keyword data quality."""

    def test_mcat_all_fcs_have_keywords(self, mcat_json: dict):
        """All MCAT foundational concepts have keywords."""
        for fc in mcat_json["foundational_concepts"]:
            assert "keywords" in fc
            assert len(fc["keywords"]) > 0, f"FC {fc['id']} has no keywords"

    def test_mcat_all_categories_have_keywords(self, mcat_json: dict):
        """All MCAT categories have keywords."""
        for fc in mcat_json["foundational_concepts"]:
            for cat in fc["categories"]:
                assert len(cat["keywords"]) > 0, f"Category {cat['id']} has no keywords"

    def test_usmle_all_systems_have_keywords(self, usmle_json: dict):
        """All USMLE systems have keywords."""
        for sys in usmle_json["systems"]:
            assert "keywords" in sys
            assert len(sys["keywords"]) > 0, f"System {sys['id']} has no keywords"

    def test_usmle_all_topics_have_keywords(self, usmle_json: dict):
        """All USMLE topics have keywords."""
        for sys in usmle_json["systems"]:
            for topic in sys["topics"]:
                assert len(topic["keywords"]) > 0, f"Topic {topic['id']} has no keywords"


class TestTaxonomyServiceIntegration:
    """Integration tests for TaxonomyService with real data."""

    def test_service_loads_both_taxonomies(self, taxonomy_service: TaxonomyService):
        """Service successfully loads both MCAT and USMLE taxonomies."""
        assert taxonomy_service.mcat_loaded
        assert taxonomy_service.usmle_loaded

    def test_total_mcat_topics(self, taxonomy_service: TaxonomyService):
        """Total MCAT topics = foundational concepts + categories."""
        topics = taxonomy_service.get_topics_by_exam(ExamType.MCAT)
        expected = (
            EXPECTED_COUNTS["mcat_foundational_concepts"]
            + EXPECTED_COUNTS["mcat_content_categories"]
        )
        assert len(topics) == expected

    def test_get_topic_by_valid_id(self, taxonomy_service: TaxonomyService):
        """Can retrieve topic by ID for both exams."""
        mcat_topic = taxonomy_service.get_topic_by_id("FC1", ExamType.MCAT)
        assert mcat_topic is not None
        assert "FC1" in mcat_topic.id

        usmle_topic = taxonomy_service.get_topic_by_id("SYS1", ExamType.USMLE_STEP1)
        assert usmle_topic is not None

    def test_search_finds_relevant_topics(self, taxonomy_service: TaxonomyService):
        """Search returns relevant topics for medical terms."""
        cardio_results = taxonomy_service.search_topics_by_keyword("cardiovascular", ExamType.MCAT)
        assert len(cardio_results) > 0

    def test_search_finds_usmle_topics(self, taxonomy_service: TaxonomyService):
        """Search works for USMLE topics."""
        results = taxonomy_service.search_topics_by_keyword("heart", ExamType.USMLE_STEP1)
        assert len(results) > 0

    def test_leaf_topics_are_categories(self, taxonomy_service: TaxonomyService):
        """All leaf topics in MCAT are content categories."""
        leaves = taxonomy_service.get_all_leaf_topics(ExamType.MCAT)
        for leaf in leaves:
            assert leaf.parent_id is not None

    def test_topic_paths_are_hierarchical(self, taxonomy_service: TaxonomyService):
        """Topic paths include parent hierarchy."""
        path = taxonomy_service.get_topic_path("1A", ExamType.MCAT)
        assert path is not None
        assert ">" in path

    @pytest.mark.asyncio
    async def test_async_get_topics(self, taxonomy_service: TaxonomyService):
        """Async get_topics method works correctly."""
        topics = await taxonomy_service.get_topics()
        assert len(topics) > 0

    @pytest.mark.asyncio
    async def test_async_search_topics(self, taxonomy_service: TaxonomyService):
        """Async search_topics method works correctly."""
        results = await taxonomy_service.search_topics("protein", limit=5)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_async_get_topic_ancestors(self, taxonomy_service: TaxonomyService):
        """Async get_topic_ancestors method works correctly."""
        ancestors = await taxonomy_service.get_topic_ancestors("1A")
        assert len(ancestors) > 0


class TestDataFileIntegrity:
    """Tests for data file integrity."""

    def test_mcat_json_is_valid(self, taxonomy_dir: Path):
        """MCAT JSON file is valid JSON."""
        mcat_path = taxonomy_dir / "mcat.json"
        assert mcat_path.exists()
        with open(mcat_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_usmle_json_is_valid(self, taxonomy_dir: Path):
        """USMLE JSON file is valid JSON."""
        usmle_path = taxonomy_dir / "usmle_step1.json"
        assert usmle_path.exists()
        with open(usmle_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_files_have_version(self, mcat_json: dict, usmle_json: dict):
        """Both taxonomy files have version information."""
        assert "version" in mcat_json
        assert "version" in usmle_json
