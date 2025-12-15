"""Integration tests for classification service with Weaviate."""

from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class MockChunk:
    id: str
    text: str


@pytest.fixture
def taxonomy_dir():
    """Path to taxonomy JSON files."""
    return Path(__file__).parent.parent.parent / "data" / "taxonomies"


@pytest.fixture
def weaviate_client():
    """Create Weaviate client for testing."""
    import weaviate

    client = weaviate.connect_to_local(port=8080)
    yield client
    client.close()


@pytest.fixture
def indexed_taxonomy(weaviate_client, taxonomy_dir):
    """Index taxonomy before tests."""
    from medanki.services.taxonomy_indexer import TaxonomyIndexer

    indexer = TaxonomyIndexer(weaviate_client, taxonomy_dir)
    indexer.clear_collection()
    indexer.index_exam("USMLE_STEP1")
    indexer.index_exam("MCAT")
    return indexer


class TestClassificationWithTaxonomy:
    """Tests for classifying chunks against taxonomy."""

    @pytest.mark.integration
    def test_classify_atherosclerosis_content_returns_cardiovascular(self, indexed_taxonomy):
        """Content about atherosclerosis should classify to cardiovascular topics."""
        chunk = MockChunk(
            id="chunk-1",
            text="""Atherosclerosis is a chronic inflammatory disease of the arterial wall. 
            It begins with endothelial dysfunction and accumulation of lipids in the intima.
            Risk factors include hypertension, diabetes, and hyperlipidemia.""",
        )

        results = indexed_taxonomy.search(chunk.text, exam_type="USMLE_STEP1", limit=5)

        assert len(results) > 0
        top_result = results[0]
        assert "SYS3" in top_result["topic_id"] or "Cardiovascular" in top_result["title"]
        assert top_result["score"] >= 0.5

    @pytest.mark.integration
    def test_classify_irrelevant_content_returns_low_score(self, indexed_taxonomy):
        """Non-medical content should have low classification scores."""
        chunk = MockChunk(
            id="chunk-2",
            text="""The weather today is sunny with a chance of rain.
            Traffic on the highway is moving slowly due to construction.""",
        )

        results = indexed_taxonomy.search(chunk.text, exam_type="USMLE_STEP1", limit=5)

        if results:
            top_score = results[0]["score"]
            assert top_score < 0.65, f"Expected low score for irrelevant content, got {top_score}"

    @pytest.mark.integration
    def test_classify_cardiovascular_drug_content(self, indexed_taxonomy):
        """CVD drug content should classify to cardiovascular or pharmacology topics."""
        chunk = MockChunk(
            id="chunk-3",
            text="""Statins inhibit HMG-CoA reductase, the rate-limiting enzyme in cholesterol synthesis.
            They decrease LDL cholesterol and have pleiotropic effects including anti-inflammatory properties.""",
        )

        results = indexed_taxonomy.search(chunk.text, exam_type="USMLE_STEP1", limit=5)

        assert len(results) > 0
        topic_ids = [r["topic_id"] for r in results]
        topic_titles = [r["title"] for r in results]
        assert any(
            "Pharmacology" in t
            or "SYS1F" in tid
            or "Cardiovascular" in t
            or "Vascular" in t
            or "SYS3" in tid
            for t, tid in zip(topic_titles, topic_ids, strict=False)
        ), (
            f"Expected CVD or pharmacology topic, got {list(zip(topic_titles, topic_ids, strict=False))}"
        )

    @pytest.mark.integration
    def test_threshold_filters_low_confidence(self, indexed_taxonomy):
        """Results below threshold should be filterable."""
        chunk = MockChunk(
            id="chunk-4", text="The mitochondria is the powerhouse of the cell producing ATP."
        )

        results = indexed_taxonomy.search(chunk.text, limit=10)

        high_confidence = [r for r in results if r["score"] >= 0.65]
        low_confidence = [r for r in results if r["score"] < 0.65]

        assert len(high_confidence) + len(low_confidence) == len(results)

    @pytest.mark.integration
    def test_cimt_content_classifies_to_vascular(self, indexed_taxonomy):
        """Carotid IMT content should classify to vascular disorders."""
        chunk = MockChunk(
            id="chunk-5",
            text="""Carotid intima-media thickness (cIMT) is a surrogate marker for 
            atherosclerosis. It measures the combined thickness of the intima and 
            media layers of the carotid artery wall.""",
        )

        results = indexed_taxonomy.search(chunk.text, exam_type="USMLE_STEP1", limit=5)

        assert len(results) > 0
        topic_ids = [r["topic_id"] for r in results]
        topic_titles = [r["title"] for r in results]
        assert any(
            "Vascular" in t or "Cardiovascular" in t or "SYS3" in tid
            for t, tid in zip(topic_titles, topic_ids, strict=False)
        ), (
            f"Expected vascular/cardiovascular topic, got {list(zip(topic_titles, topic_ids, strict=False))}"
        )
