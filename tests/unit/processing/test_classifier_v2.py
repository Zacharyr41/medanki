"""Tests for ClassificationServiceV2 with TaxonomyServiceV2."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

import pytest

from medanki.models.enums import ExamType
from medanki.models.taxonomy import NodeType
from medanki.processing.classifier import ClassificationServiceV2, TopicMatch
from medanki.storage.taxonomy_repository import TaxonomyRepository


@dataclass
class MockChunk:
    """Mock chunk for testing."""

    id: str
    text: str


@pytest.fixture
async def db_path(tmp_path: Path) -> Path:
    """Return temp database path."""
    return tmp_path / "taxonomy_test.db"


@pytest.fixture
async def repo(db_path: Path) -> AsyncGenerator[TaxonomyRepository, None]:
    """Create initialized repository with test data."""
    r = TaxonomyRepository(db_path)
    await r.initialize()

    await r.insert_exam({"id": "MCAT", "name": "MCAT"})
    await r.insert_exam({"id": "USMLE_STEP1", "name": "USMLE Step 1"})

    await r.insert_node(
        {
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": NodeType.FOUNDATIONAL_CONCEPT.value,
            "code": "FC1",
            "title": "Biomolecules",
        }
    )
    await r.insert_node(
        {
            "id": "1A",
            "exam_id": "MCAT",
            "node_type": NodeType.CONTENT_CATEGORY.value,
            "code": "1A",
            "title": "Proteins",
            "parent_id": "FC1",
        }
    )
    await r.insert_node(
        {
            "id": "CARDIO",
            "exam_id": "USMLE_STEP1",
            "node_type": NodeType.ORGAN_SYSTEM.value,
            "code": "CARDIO",
            "title": "Cardiovascular",
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


class MockVectorStore:
    """Mock async vector store for testing."""

    def __init__(self, results: list[dict] | None = None):
        self._results = results or []

    async def hybrid_search(self, query: str, alpha: float = 0.5, **kwargs) -> list[dict]:
        """Return mock search results."""
        return self._results


class TestClassificationServiceV2:
    """Tests for ClassificationServiceV2."""

    @pytest.mark.asyncio
    async def test_classify_returns_topic_matches(self, taxonomy_service):
        """Classifies chunk and returns TopicMatch list."""
        vector_store = MockVectorStore(
            [
                {"topic_id": "FC1", "score": 0.95},
                {"topic_id": "1A", "score": 0.85},
            ]
        )

        service = ClassificationServiceV2(taxonomy_service, vector_store)
        chunk = MockChunk(id="test", text="protein structure and function")

        matches = await service.classify(chunk)

        assert len(matches) == 2
        assert all(isinstance(m, TopicMatch) for m in matches)
        assert matches[0].topic_id == "FC1"
        assert matches[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_classify_empty_text_returns_empty(self, taxonomy_service):
        """Returns empty list for empty text."""
        vector_store = MockVectorStore([])
        service = ClassificationServiceV2(taxonomy_service, vector_store)
        chunk = MockChunk(id="test", text="")

        matches = await service.classify(chunk)

        assert matches == []

    @pytest.mark.asyncio
    async def test_classify_applies_thresholds(self, taxonomy_service):
        """Filters matches below threshold."""
        vector_store = MockVectorStore(
            [
                {"topic_id": "FC1", "score": 0.90},
                {"topic_id": "1A", "score": 0.50},
            ]
        )

        service = ClassificationServiceV2(taxonomy_service, vector_store, base_threshold=0.65)
        chunk = MockChunk(id="test", text="protein synthesis")

        matches = await service.classify(chunk)

        assert len(matches) == 1
        assert matches[0].topic_id == "FC1"

    @pytest.mark.asyncio
    async def test_classify_with_exam_filter(self, taxonomy_service):
        """Filters results by exam type."""
        vector_store = MockVectorStore(
            [
                {"topic_id": "FC1", "score": 0.90},
                {"topic_id": "CARDIO", "score": 0.85},
            ]
        )

        service = ClassificationServiceV2(taxonomy_service, vector_store)
        chunk = MockChunk(id="test", text="cardiovascular physiology")

        matches = await service.classify(chunk, exam_type=ExamType.MCAT)

        mcat_ids = [m.topic_id for m in matches]
        assert "CARDIO" not in mcat_ids
        assert "FC1" in mcat_ids

    @pytest.mark.asyncio
    async def test_classify_includes_topic_name(self, taxonomy_service):
        """Includes topic title in match."""
        vector_store = MockVectorStore(
            [
                {"topic_id": "FC1", "score": 0.90},
            ]
        )

        service = ClassificationServiceV2(taxonomy_service, vector_store)
        chunk = MockChunk(id="test", text="biomolecule structure")

        matches = await service.classify(chunk)

        assert matches[0].topic_name == "Biomolecules"

    @pytest.mark.asyncio
    async def test_classify_with_path_returns_hierarchy(self, taxonomy_service):
        """Returns hierarchical path with matches."""
        vector_store = MockVectorStore(
            [
                {"topic_id": "1A", "score": 0.90},
            ]
        )

        service = ClassificationServiceV2(taxonomy_service, vector_store)
        chunk = MockChunk(id="test", text="protein")

        results = await service.classify_with_path(chunk)

        assert len(results) == 1
        match, path = results[0]
        assert match.topic_id == "1A"
        assert "Biomolecules" in path
        assert "Proteins" in path


class TestDetectPrimaryExam:
    """Tests for detect_primary_exam method."""

    @pytest.mark.asyncio
    async def test_detect_mcat_higher_score(self, taxonomy_service):
        """Detects MCAT when MCAT scores higher."""

        class ExamFilterVectorStore:
            async def hybrid_search(self, query: str, alpha: float = 0.5, **kwargs):
                exam_filter = kwargs.get("exam_filter", "")
                if exam_filter == "MCAT":
                    return [{"topic_id": "FC1", "score": 0.95}]
                return [{"topic_id": "CARDIO", "score": 0.80}]

        service = ClassificationServiceV2(taxonomy_service, ExamFilterVectorStore())
        chunk = MockChunk(id="test", text="amino acid metabolism")

        result = await service.detect_primary_exam(chunk)

        assert result == "mcat"

    @pytest.mark.asyncio
    async def test_detect_usmle_higher_score(self, taxonomy_service):
        """Detects USMLE when USMLE scores higher."""

        class ExamFilterVectorStore:
            async def hybrid_search(self, query: str, alpha: float = 0.5, **kwargs):
                exam_filter = kwargs.get("exam_filter", "")
                if exam_filter == "USMLE_STEP1":
                    return [{"topic_id": "CARDIO", "score": 0.95}]
                return [{"topic_id": "FC1", "score": 0.80}]

        service = ClassificationServiceV2(taxonomy_service, ExamFilterVectorStore())
        chunk = MockChunk(id="test", text="heart failure pathophysiology")

        result = await service.detect_primary_exam(chunk)

        assert result == "usmle_step1"
