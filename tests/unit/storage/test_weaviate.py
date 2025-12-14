from unittest.mock import Mock
from uuid import uuid4

import pytest

from medanki.storage.weaviate import MedicalChunk, WeaviateStore


class TestWeaviateConnection:
    def test_connects_to_weaviate(self, mock_weaviate_client):
        store = WeaviateStore(client=mock_weaviate_client)

        assert store.client is not None
        mock_weaviate_client.is_ready.assert_called_once()

    def test_creates_schema_if_missing(self, mock_weaviate_client):
        mock_weaviate_client.collections.exists.return_value = False

        WeaviateStore(client=mock_weaviate_client)

        mock_weaviate_client.collections.create.assert_called_once()
        call_kwargs = mock_weaviate_client.collections.create.call_args
        assert call_kwargs[1]["name"] == "MedicalChunk"

    def test_health_check(self, mock_weaviate_client):
        mock_weaviate_client.is_ready.return_value = True
        store = WeaviateStore(client=mock_weaviate_client)

        assert store.health_check() is True


class TestWeaviateCRUD:
    @pytest.fixture
    def medical_chunk(self):
        return MedicalChunk(
            id="chunk_001",
            content="The cardiac cycle consists of systole and diastole phases.",
            embedding=[0.1] * 384,
            document_id="doc_001",
            exam_type="USMLE",
            metadata={"page": 1}
        )

    def test_upsert_single_chunk(self, mock_weaviate_client, medical_chunk):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        chunk_id = store.upsert(medical_chunk)

        assert chunk_id is not None
        collection.data.insert.assert_called_once()

    def test_upsert_batch(self, mock_weaviate_client, sample_chunks_with_embeddings):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        chunk_ids = store.upsert_batch(sample_chunks_with_embeddings)

        assert len(chunk_ids) == len(sample_chunks_with_embeddings)
        collection.data.insert_many.assert_called_once()

    def test_get_by_id(self, mock_weaviate_client, medical_chunk):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        mock_obj = Mock()
        mock_obj.properties = {
            "content": medical_chunk.content,
            "document_id": medical_chunk.document_id,
            "exam_type": medical_chunk.exam_type,
        }
        mock_obj.vector = {"default": medical_chunk.embedding}
        mock_obj.uuid = medical_chunk.id
        collection.query.fetch_object_by_id.return_value = mock_obj

        result = store.get_by_id(medical_chunk.id)

        assert result is not None
        assert result.content == medical_chunk.content
        collection.query.fetch_object_by_id.assert_called_once_with(medical_chunk.id, include_vector=True)

    def test_delete_by_id(self, mock_weaviate_client, sample_chunk):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        store.delete(sample_chunk.id)

        collection.data.delete_by_id.assert_called_once_with(sample_chunk.id)


class TestWeaviateSearch:
    def test_vector_search(self, mock_weaviate_client, sample_chunks_with_embeddings):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        mock_results = Mock()
        mock_results.objects = [
            Mock(
                properties={"content": c.content, "document_id": c.document_id, "exam_type": c.exam_type},
                vector={"default": c.embedding},
                uuid=c.id,
                metadata=Mock(distance=0.1 * i)
            )
            for i, c in enumerate(sample_chunks_with_embeddings[:3])
        ]
        collection.query.near_vector.return_value = mock_results

        query_embedding = [0.1] * 384
        results = store.vector_search(query_embedding, limit=3)

        assert len(results) == 3
        collection.query.near_vector.assert_called_once()

    def test_keyword_search_bm25(self, mock_weaviate_client, sample_chunks_with_embeddings):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        mock_results = Mock()
        mock_results.objects = [
            Mock(
                properties={"content": "CHF treatment guidelines", "document_id": "doc1", "exam_type": "USMLE"},
                vector={"default": [0.1] * 384},
                uuid=str(uuid4()),
                metadata=Mock(score=0.9)
            )
        ]
        collection.query.bm25.return_value = mock_results

        results = store.keyword_search("CHF", limit=5)

        assert len(results) >= 1
        assert any("CHF" in r.chunk.content for r in results)
        collection.query.bm25.assert_called_once()

    def test_hybrid_search(self, mock_weaviate_client, sample_chunks_with_embeddings):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        mock_results = Mock()
        mock_results.objects = [
            Mock(
                properties={"content": c.content, "document_id": c.document_id, "exam_type": c.exam_type},
                vector={"default": c.embedding},
                uuid=c.id,
                metadata=Mock(score=0.8)
            )
            for c in sample_chunks_with_embeddings[:2]
        ]
        collection.query.hybrid.return_value = mock_results

        query_embedding = [0.1] * 384
        results = store.hybrid_search("heart failure", query_embedding, alpha=0.5, limit=5)

        assert len(results) >= 1
        call_kwargs = collection.query.hybrid.call_args
        assert call_kwargs[1]["alpha"] == 0.5

    def test_search_with_filters(self, mock_weaviate_client, sample_chunks_with_embeddings):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        mock_results = Mock()
        mock_results.objects = [
            Mock(
                properties={"content": "Filtered content", "document_id": "doc123", "exam_type": "USMLE"},
                vector={"default": [0.1] * 384},
                uuid=str(uuid4()),
                metadata=Mock(distance=0.1)
            )
        ]
        collection.query.near_vector.return_value = mock_results

        query_embedding = [0.1] * 384
        results = store.vector_search(
            query_embedding,
            limit=5,
            filters={"exam_type": "USMLE", "document_id": "doc123"}
        )

        assert len(results) >= 1
        call_kwargs = collection.query.near_vector.call_args
        assert call_kwargs[1].get("filters") is not None

    def test_search_returns_scores(self, mock_weaviate_client, sample_chunks_with_embeddings):
        store = WeaviateStore(client=mock_weaviate_client)
        collection = mock_weaviate_client.collections.get.return_value

        mock_results = Mock()
        mock_results.objects = [
            Mock(
                properties={"content": c.content, "document_id": c.document_id, "exam_type": c.exam_type},
                vector={"default": c.embedding},
                uuid=c.id,
                metadata=Mock(distance=0.1, score=0.9)
            )
            for c in sample_chunks_with_embeddings[:2]
        ]
        collection.query.near_vector.return_value = mock_results

        query_embedding = [0.1] * 384
        results = store.vector_search(query_embedding, limit=5)

        for result in results:
            assert hasattr(result, 'score')
            assert result.score is not None
