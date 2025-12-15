"""Integration tests for taxonomy indexing to Weaviate."""

from pathlib import Path

import pytest


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


class TestTaxonomyIndexing:
    """Tests for indexing taxonomy topics to Weaviate."""

    @pytest.mark.integration
    def test_index_usmle_topics_to_weaviate(self, taxonomy_dir, weaviate_client):
        """Should index USMLE topics with embeddings."""
        from medanki.services.taxonomy_indexer import TaxonomyIndexer

        indexer = TaxonomyIndexer(weaviate_client, taxonomy_dir)
        count = indexer.index_exam("USMLE_STEP1")

        assert count > 0

        collection = weaviate_client.collections.get("TaxonomyTopic")
        result = collection.query.fetch_objects(limit=1)
        assert len(result.objects) > 0

    @pytest.mark.integration
    def test_index_mcat_topics_to_weaviate(self, taxonomy_dir, weaviate_client):
        """Should index MCAT topics with embeddings."""
        from medanki.services.taxonomy_indexer import TaxonomyIndexer

        indexer = TaxonomyIndexer(weaviate_client, taxonomy_dir)
        count = indexer.index_exam("MCAT")

        assert count > 0

    @pytest.mark.integration
    def test_search_returns_cardiovascular_for_atherosclerosis_query(
        self, taxonomy_dir, weaviate_client
    ):
        """Searching for atherosclerosis should return cardiovascular topics."""
        from medanki.services.taxonomy_indexer import TaxonomyIndexer

        indexer = TaxonomyIndexer(weaviate_client, taxonomy_dir)
        indexer.index_exam("USMLE_STEP1")

        results = indexer.search("atherosclerosis carotid artery thickness", limit=5)

        assert len(results) > 0
        topic_ids = [r["topic_id"] for r in results]
        assert any("SYS3" in tid for tid in topic_ids), (
            f"Expected cardiovascular topic, got {topic_ids}"
        )

    @pytest.mark.integration
    def test_hybrid_search_balances_keyword_and_semantic(self, taxonomy_dir, weaviate_client):
        """Hybrid search should find topics by keywords AND semantic meaning."""
        from medanki.services.taxonomy_indexer import TaxonomyIndexer

        indexer = TaxonomyIndexer(weaviate_client, taxonomy_dir)
        indexer.index_exam("USMLE_STEP1")

        keyword_results = indexer.search("hypertension", alpha=0.0, limit=5)
        semantic_results = indexer.search("high blood pressure in arteries", alpha=1.0, limit=5)
        hybrid_results = indexer.search("hypertension blood pressure", alpha=0.5, limit=5)

        assert len(keyword_results) > 0
        assert len(semantic_results) > 0
        assert len(hybrid_results) > 0
