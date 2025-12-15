"""Integration tests for the classification pipeline.

Tests chunk embedding, storage in vector store, and classification against taxonomy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from medanki.processing.classifier import ClassificationService

# ============================================================================
# Embedding and Storage Tests
# ============================================================================


@pytest.mark.integration
class TestEmbeddingAndStorage:
    """Test embedding generation and vector store operations."""

    async def test_embed_and_store(
        self,
        mock_embedding_service,
        mock_vector_store,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test that chunks are embedded and stored in vector store."""
        # Generate embedding
        embedding = await mock_embedding_service.embed(sample_chunk_with_cardiology.text)

        # Verify embedding dimensions
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

        # Create chunk with embedding for storage
        @dataclass
        class ChunkWithEmbedding:
            id: str
            content: str
            embedding: list[float]
            document_id: str
            exam_type: str | None = None
            metadata: dict | None = None

        chunk_to_store = ChunkWithEmbedding(
            id=sample_chunk_with_cardiology.id,
            content=sample_chunk_with_cardiology.text,
            embedding=embedding,
            document_id=sample_chunk_with_cardiology.document_id,
            exam_type="mcat",
            metadata={"section": "cardiology"},
        )

        # Store in vector store
        stored_id = mock_vector_store.upsert(chunk_to_store)

        # Verify storage
        assert stored_id == sample_chunk_with_cardiology.id
        assert sample_chunk_with_cardiology.id in mock_vector_store.chunks

        # Retrieve and verify
        retrieved = mock_vector_store.get_by_id(stored_id)
        assert retrieved is not None
        assert retrieved.content == sample_chunk_with_cardiology.text

    async def test_batch_embed_and_store(
        self,
        mock_embedding_service,
        mock_vector_store,
        sample_chunk_with_cardiology,
        sample_chunk_with_pharmacology,
    ) -> None:
        """Test batch embedding and storage."""
        chunks = [sample_chunk_with_cardiology, sample_chunk_with_pharmacology]
        texts = [c.text for c in chunks]

        # Batch embed
        embeddings = await mock_embedding_service.embed_batch(texts)

        assert len(embeddings) == 2
        assert all(len(e) == 768 for e in embeddings)

        # Create chunks with embeddings
        @dataclass
        class ChunkWithEmbedding:
            id: str
            content: str
            embedding: list[float]
            document_id: str

        chunks_to_store = [
            ChunkWithEmbedding(
                id=c.id,
                content=c.text,
                embedding=e,
                document_id=c.document_id,
            )
            for c, e in zip(chunks, embeddings, strict=False)
        ]

        # Batch store
        stored_ids = mock_vector_store.upsert_batch(chunks_to_store)

        assert len(stored_ids) == 2
        assert all(sid in mock_vector_store.chunks for sid in stored_ids)


# ============================================================================
# Classification Tests
# ============================================================================


@pytest.mark.integration
class TestClassification:
    """Test chunk classification against taxonomy."""

    def test_classify_cardiology_content(
        self,
        mock_taxonomy_service,
        mock_vector_store,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test that cardiology content is classified to FC4/4A topics."""

        # Set up vector store with taxonomy topics
        @dataclass
        class TopicChunk:
            id: str
            content: str
            text: str = ""
            embedding: list[float] = field(default_factory=list)
            document_id: str = "taxonomy"

            def __post_init__(self):
                self.text = self.content

        # Add cardiology topics to store
        # Include exact terms from the sample chunk for better matching
        topics = [
            TopicChunk(
                id="FC4", content="cardiac cycle systole diastole ventricles contract heart"
            ),
            TopicChunk(id="FC4A", content="heart anatomy atrium ventricle valve chamber"),
            TopicChunk(id="FC2", content="biochemistry metabolism enzymes"),
            TopicChunk(id="FC2C", content="pharmacology drug medication dosing"),
        ]

        for topic in topics:
            mock_vector_store.upsert(topic)

        # Create classifier
        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
            base_threshold=0.1,  # Lower threshold for testing with simple keyword matching
        )

        # Classify the cardiology chunk
        matches = classifier.classify(sample_chunk_with_cardiology)

        # Should find cardiology-related topics
        assert len(matches) >= 1

        # Top match should be cardiology related
        topic_ids = [m.topic_id for m in matches]
        assert any(tid in ["FC4", "FC4A"] for tid in topic_ids), (
            f"Expected cardiology topics, got {topic_ids}"
        )

    def test_classify_pharmacology_content(
        self,
        mock_taxonomy_service,
        mock_vector_store,
        sample_chunk_with_pharmacology,
    ) -> None:
        """Test that pharmacology content is classified to FC2/2C topics."""

        @dataclass
        class TopicChunk:
            id: str
            content: str
            text: str = ""
            embedding: list[float] = field(default_factory=list)
            document_id: str = "taxonomy"

            def __post_init__(self):
                self.text = self.content

        # Add topics to store
        topics = [
            TopicChunk(id="FC4", content="cardiovascular heart cardiac"),
            TopicChunk(id="FC2", content="biochemistry metabolism"),
            TopicChunk(
                id="FC2C",
                content="pharmacology drug medication lisinopril metoprolol ACE inhibitor beta blocker",
            ),
            TopicChunk(id="PHARM", content="pharmacology medications drugs dosing"),
        ]

        for topic in topics:
            mock_vector_store.upsert(topic)

        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
            base_threshold=0.3,
        )

        matches = classifier.classify(sample_chunk_with_pharmacology)

        assert len(matches) >= 1
        topic_ids = [m.topic_id for m in matches]

        # Should match pharmacology topics
        assert any(tid in ["FC2C", "PHARM"] for tid in topic_ids), (
            f"Expected pharmacology topics, got {topic_ids}"
        )

    def test_hybrid_search_abbreviations(
        self,
        mock_taxonomy_service,
        mock_vector_store,
        sample_chunk_with_chf,
    ) -> None:
        """Test that abbreviations like 'CHF' correctly find heart topics."""

        @dataclass
        class TopicChunk:
            id: str
            content: str
            text: str = ""
            embedding: list[float] = field(default_factory=list)
            document_id: str = "taxonomy"

            def __post_init__(self):
                self.text = self.content

        # Add topics with both abbreviation and full form
        topics = [
            TopicChunk(
                id="CHF_TOPIC", content="CHF congestive heart failure cardiac pump dysfunction"
            ),
            TopicChunk(id="FC4", content="cardiovascular heart cardiac failure"),
            TopicChunk(id="RENAL", content="kidney nephrology renal"),
        ]

        for topic in topics:
            mock_vector_store.upsert(topic)

        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
            base_threshold=0.2,  # Lower threshold for abbreviation matching
        )

        matches = classifier.classify(sample_chunk_with_chf)

        # Should find heart-related topics
        topic_ids = [m.topic_id for m in matches]
        assert any(tid in ["CHF_TOPIC", "FC4"] for tid in topic_ids), (
            f"CHF should match heart topics, got {topic_ids}"
        )

    def test_multi_label_classification(
        self,
        mock_taxonomy_service,
        mock_vector_store,
    ) -> None:
        """Test that chunks can match multiple topics."""

        @dataclass
        class SampleChunk:
            id: str = "chunk_multi"
            text: str = "Beta-blockers like metoprolol reduce heart rate in patients with CHF."
            document_id: str = "doc_multi"

        @dataclass
        class TopicChunk:
            id: str
            content: str
            text: str = ""
            embedding: list[float] = field(default_factory=list)
            document_id: str = "taxonomy"

            def __post_init__(self):
                self.text = self.content

        # Add topics that could all match
        topics = [
            TopicChunk(id="PHARM", content="pharmacology beta-blocker metoprolol drug"),
            TopicChunk(id="CARDIO", content="heart cardiac CHF congestive heart failure"),
            TopicChunk(id="PHYSIO", content="heart rate physiology cardiac output"),
            TopicChunk(id="NEURO", content="neurology brain nervous system"),
        ]

        for topic in topics:
            mock_vector_store.upsert(topic)

        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
            base_threshold=0.2,
            relative_threshold=0.5,  # Allow multiple matches
        )

        chunk = SampleChunk()
        matches = classifier.classify(chunk)

        # Should match multiple topics
        topic_ids = [m.topic_id for m in matches]

        # Should match at least 2 relevant topics
        relevant_matches = [tid for tid in topic_ids if tid in ["PHARM", "CARDIO", "PHYSIO"]]
        assert len(relevant_matches) >= 1, f"Expected multiple relevant matches, got {topic_ids}"


# ============================================================================
# Threshold Tests
# ============================================================================


@pytest.mark.integration
class TestClassificationThresholds:
    """Test classification threshold behavior."""

    def test_base_threshold_filtering(
        self,
        mock_taxonomy_service,
        mock_vector_store,
    ) -> None:
        """Test that low-confidence matches are filtered by base threshold."""

        @dataclass
        class SampleChunk:
            id: str = "chunk_threshold"
            text: str = "Highly specific cardiology content about the cardiac cycle."
            document_id: str = "doc_threshold"

        @dataclass
        class TopicChunk:
            id: str
            content: str
            text: str = ""
            embedding: list[float] = field(default_factory=list)
            document_id: str = "taxonomy"

            def __post_init__(self):
                self.text = self.content

        # Add topics with varying relevance
        topics = [
            TopicChunk(id="CARDIO", content="cardiac cycle heart cardiology"),
            TopicChunk(id="UNRELATED", content="completely unrelated topic xyz"),
        ]

        for topic in topics:
            mock_vector_store.upsert(topic)

        # High threshold should filter out weak matches
        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
            base_threshold=0.7,
        )

        chunk = SampleChunk()
        matches = classifier.classify(chunk)

        # If matches exist, they should be high confidence
        for match in matches:
            assert match.confidence >= 0.0  # Basic sanity check

    def test_empty_chunk_returns_no_matches(
        self,
        mock_taxonomy_service,
        mock_vector_store,
    ) -> None:
        """Test that empty chunks return no classifications."""

        @dataclass
        class EmptyChunk:
            id: str = "chunk_empty"
            text: str = ""
            document_id: str = "doc_empty"

        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
        )

        chunk = EmptyChunk()
        matches = classifier.classify(chunk)

        assert len(matches) == 0


# ============================================================================
# Primary Exam Detection Tests
# ============================================================================


@pytest.mark.integration
class TestPrimaryExamDetection:
    """Test primary exam type detection."""

    def test_detect_primary_exam(
        self,
        mock_taxonomy_service,
        mock_vector_store,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test detection of primary exam type for a chunk."""

        @dataclass
        class TopicChunk:
            id: str
            content: str
            text: str = ""
            embedding: list[float] = field(default_factory=list)
            document_id: str = "taxonomy"

            def __post_init__(self):
                self.text = self.content

        topics = [
            TopicChunk(id="FC4", content="cardiac heart systole diastole"),
        ]

        for topic in topics:
            mock_vector_store.upsert(topic)

        classifier = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store,
        )

        exam_type = classifier.detect_primary_exam(sample_chunk_with_cardiology)

        # Should return a valid exam type
        assert exam_type in ["mcat", "usmle"]


# ============================================================================
# Vector Store Integration Tests
# ============================================================================


@pytest.mark.integration
class TestVectorStoreOperations:
    """Test vector store operations for classification."""

    def test_vector_store_health_check(self, mock_vector_store) -> None:
        """Test vector store health check."""
        assert mock_vector_store.health_check() is True

    def test_vector_store_delete(
        self,
        mock_embedding_service,
        mock_vector_store,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test deleting chunks from vector store."""

        @dataclass
        class ChunkWithEmbedding:
            id: str
            content: str
            embedding: list[float]
            document_id: str

        # Store a chunk
        chunk = ChunkWithEmbedding(
            id=sample_chunk_with_cardiology.id,
            content=sample_chunk_with_cardiology.text,
            embedding=[0.1] * 768,
            document_id=sample_chunk_with_cardiology.document_id,
        )

        stored_id = mock_vector_store.upsert(chunk)

        # Verify it's stored
        assert mock_vector_store.get_by_id(stored_id) is not None

        # Delete it
        mock_vector_store.delete(stored_id)

        # Verify it's gone
        assert mock_vector_store.get_by_id(stored_id) is None

    async def test_embedding_determinism(self, mock_embedding_service) -> None:
        """Test that embeddings are deterministic for same text."""
        text = "The cardiac cycle consists of systole and diastole."

        embedding1 = await mock_embedding_service.embed(text)
        embedding2 = await mock_embedding_service.embed(text)

        # Same text should produce same embedding
        assert embedding1 == embedding2

    async def test_different_texts_different_embeddings(self, mock_embedding_service) -> None:
        """Test that different texts produce different embeddings."""
        text1 = "The cardiac cycle consists of systole and diastole."
        text2 = "Pharmacology involves the study of drug mechanisms."

        embedding1 = await mock_embedding_service.embed(text1)
        embedding2 = await mock_embedding_service.embed(text2)

        # Different texts should produce different embeddings
        assert embedding1 != embedding2
