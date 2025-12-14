"""Tests for the taxonomy service."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from medanki.services.taxonomy import TaxonomyService


@pytest.fixture
def taxonomy_dir() -> Path:
    """Return the path to taxonomy data files."""
    return Path(__file__).parent.parent.parent.parent / "data" / "taxonomies"


@pytest.fixture
def taxonomy_service(taxonomy_dir: Path) -> TaxonomyService:
    """Create a taxonomy service instance."""
    from medanki.services.taxonomy import TaxonomyService

    return TaxonomyService(taxonomy_dir)


class TestTaxonomyLoading:
    """Tests for taxonomy loading functionality."""

    def test_loads_mcat_taxonomy(
        self, taxonomy_service: TaxonomyService, taxonomy_dir: Path
    ) -> None:
        """Loads data/taxonomies/mcat.json."""
        assert (taxonomy_dir / "mcat.json").exists()
        assert taxonomy_service.mcat_loaded

    def test_loads_usmle_taxonomy(
        self, taxonomy_service: TaxonomyService, taxonomy_dir: Path
    ) -> None:
        """Loads data/taxonomies/usmle_step1.json."""
        assert (taxonomy_dir / "usmle_step1.json").exists()
        assert taxonomy_service.usmle_loaded

    def test_taxonomy_has_foundational_concepts(
        self, taxonomy_service: TaxonomyService
    ) -> None:
        """MCAT has 10 foundational concepts."""
        from medanki.services.taxonomy import ExamType

        fcs = taxonomy_service.get_foundational_concepts(ExamType.MCAT)
        assert len(fcs) == 10

    def test_taxonomy_has_content_categories(
        self, taxonomy_service: TaxonomyService
    ) -> None:
        """MCAT has 23 content categories across all FCs."""
        from medanki.services.taxonomy import ExamType

        categories = taxonomy_service.get_content_categories(ExamType.MCAT)
        assert len(categories) == 23

    def test_topic_has_required_fields(
        self, taxonomy_service: TaxonomyService
    ) -> None:
        """Topic has id, title, path, keywords."""
        from medanki.services.taxonomy import ExamType

        topic = taxonomy_service.get_topic_by_id("1A", ExamType.MCAT)
        assert topic is not None
        assert topic.id == "1A"
        assert topic.title is not None
        assert topic.path is not None
        assert topic.keywords is not None


class TestTopicRetrieval:
    """Tests for topic retrieval functionality."""

    def test_get_topic_by_id(self, taxonomy_service: TaxonomyService) -> None:
        """Returns topic by ID."""
        from medanki.services.taxonomy import ExamType

        topic = taxonomy_service.get_topic_by_id("FC1", ExamType.MCAT)
        assert topic is not None
        assert topic.id == "FC1"

        topic = taxonomy_service.get_topic_by_id("1A", ExamType.MCAT)
        assert topic is not None
        assert topic.id == "1A"

    def test_get_topic_by_id_not_found(
        self, taxonomy_service: TaxonomyService
    ) -> None:
        """Returns None for non-existent topic ID."""
        from medanki.services.taxonomy import ExamType

        topic = taxonomy_service.get_topic_by_id("INVALID", ExamType.MCAT)
        assert topic is None

    def test_get_topics_by_exam(self, taxonomy_service: TaxonomyService) -> None:
        """Filter topics by ExamType.MCAT."""
        from medanki.services.taxonomy import ExamType

        topics = taxonomy_service.get_topics_by_exam(ExamType.MCAT)
        assert len(topics) > 0
        for topic in topics:
            assert topic.exam_type == ExamType.MCAT

    def test_get_topics_by_exam_usmle(self, taxonomy_service: TaxonomyService) -> None:
        """Filter topics by ExamType.USMLE_STEP1."""
        from medanki.services.taxonomy import ExamType

        topics = taxonomy_service.get_topics_by_exam(ExamType.USMLE_STEP1)
        assert len(topics) > 0
        for topic in topics:
            assert topic.exam_type == ExamType.USMLE_STEP1


class TestTopicSearch:
    """Tests for topic search functionality."""

    def test_search_topics_by_keyword(
        self, taxonomy_service: TaxonomyService
    ) -> None:
        """Search 'cardiovascular' finds heart-related topics."""
        from medanki.services.taxonomy import ExamType

        results = taxonomy_service.search_topics_by_keyword(
            "cardiovascular", ExamType.MCAT
        )
        assert len(results) > 0
        found_cardio = any("cardiovascular" in t.title.lower() or
                          "cardiovascular" in [k.lower() for k in t.keywords]
                          for t in results)
        assert found_cardio

    def test_search_topics_by_keyword_case_insensitive(
        self, taxonomy_service: TaxonomyService
    ) -> None:
        """Keyword search is case-insensitive."""
        from medanki.services.taxonomy import ExamType

        results_lower = taxonomy_service.search_topics_by_keyword(
            "amino", ExamType.MCAT
        )
        results_upper = taxonomy_service.search_topics_by_keyword(
            "AMINO", ExamType.MCAT
        )
        assert len(results_lower) == len(results_upper)


class TestTopicPath:
    """Tests for topic path functionality."""

    def test_get_topic_path(self, taxonomy_service: TaxonomyService) -> None:
        """Returns path like 'FC1 > 1A'."""
        from medanki.services.taxonomy import ExamType

        path = taxonomy_service.get_topic_path("1A", ExamType.MCAT)
        assert path is not None
        assert "FC1" in path
        assert "1A" in path
        assert ">" in path

    def test_get_topic_path_for_fc(self, taxonomy_service: TaxonomyService) -> None:
        """Returns just the FC title for foundational concepts."""
        from medanki.services.taxonomy import ExamType

        path = taxonomy_service.get_topic_path("FC1", ExamType.MCAT)
        assert path is not None
        assert ">" not in path

    def test_get_all_leaf_topics(self, taxonomy_service: TaxonomyService) -> None:
        """Returns lowest-level topics only (content categories)."""
        from medanki.services.taxonomy import ExamType

        leaves = taxonomy_service.get_all_leaf_topics(ExamType.MCAT)
        assert len(leaves) > 0
        for leaf in leaves:
            assert leaf.parent_id is not None
