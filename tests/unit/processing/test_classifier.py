"""Tests for the classification service."""

from __future__ import annotations

from medanki.processing.classifier import ClassificationService, TopicMatch


class TestBasicClassification:
    """Tests for basic chunk classification."""

    def test_classifies_chunk_to_topics(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """Returns list of TopicMatch for a chunk."""
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, TopicMatch) for r in results)

    def test_returns_confidence_scores(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """Each match has confidence score between 0 and 1."""
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        for match in results:
            assert hasattr(match, 'confidence')
            assert 0.0 <= match.confidence <= 1.0

    def test_respects_threshold(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """Only returns matches with confidence >= 0.65."""
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        for match in results:
            assert match.confidence >= 0.65, f"Match {match.topic_id} has confidence {match.confidence} < 0.65"

    def test_empty_chunk_returns_empty(self, empty_chunk, mock_taxonomy_service, mock_vector_store):
        """Empty text returns no matches."""
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(empty_chunk)

        assert results == []


class TestMultiLabel:
    """Tests for multi-label classification."""

    def test_returns_multiple_topics(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """A chunk can match multiple topics."""
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "cardio_001", "score": 0.92},
            {"topic_id": "physio_001", "score": 0.85},
            {"topic_id": "anatomy_001", "score": 0.78},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        assert len(results) >= 2, "Should return multiple topic matches"

    def test_primary_topic_is_highest_score(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """First result is the best match (highest confidence)."""
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "cardio_001", "score": 0.92},
            {"topic_id": "physio_001", "score": 0.85},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        assert len(results) >= 1
        assert results[0].confidence >= max(r.confidence for r in results)

    def test_relative_threshold(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """Results within 80% of top score are included."""
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "cardio_001", "score": 0.90},
            {"topic_id": "physio_001", "score": 0.75},
            {"topic_id": "anatomy_001", "score": 0.60},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        confidences = [r.confidence for r in results]
        top_score = max(confidences) if confidences else 0
        relative_threshold = top_score * 0.80

        for match in results:
            assert match.confidence >= relative_threshold, (
                f"Match {match.topic_id} has confidence {match.confidence} "
                f"below relative threshold {relative_threshold}"
            )


class TestPharmacologyClassification:
    """Tests for pharmacology content classification."""

    def test_classify_pharmacology_content(self, mock_taxonomy_service, mock_vector_store):
        """Pharmacology content is classified to drug-related topics."""
        from tests.conftest import Chunk

        pharmacology_chunk = Chunk(
            id="chunk_pharm_001",
            document_id="doc_pharm",
            text="Metformin is a biguanide drug used for type 2 diabetes. It decreases hepatic glucose production.",
            start_char=0,
            end_char=100,
            token_count=20,
        )

        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "pharmacology_endocrine_001", "score": 0.90},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(pharmacology_chunk)

        topic_ids = [r.topic_id for r in results]
        assert any("pharm" in tid.lower() or "drug" in tid.lower() or "endocrine" in tid.lower() for tid in topic_ids), (
            f"Pharmacology content should map to drug-related topics, got: {topic_ids}"
        )


class TestMaxTopicsLimit:
    """Tests for max topics limit via relative threshold."""

    def test_classify_filters_by_relative_threshold(self, sample_cardiology_chunk, mock_taxonomy_service, mock_vector_store):
        """Classification filters low-confidence topics via relative threshold."""
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "topic_0", "score": 0.90},
            {"topic_id": "topic_1", "score": 0.85},
            {"topic_id": "topic_2", "score": 0.75},
            {"topic_id": "topic_3", "score": 0.50},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_cardiology_chunk)

        confidences = [r.confidence for r in results]
        if len(confidences) > 0:
            max_conf = max(confidences)
            for conf in confidences:
                assert conf >= max_conf * 0.80, "All results should pass relative threshold"


class TestMedicalAbbreviations:
    """Tests for medical abbreviation handling."""

    def test_matches_chf_to_cardiology(self, sample_chf_chunk, mock_taxonomy_service, mock_vector_store):
        """CHF abbreviation maps to cardiovascular topics."""
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "cardiovascular_heart_failure", "score": 0.88},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_chf_chunk)

        topic_ids = [r.topic_id for r in results]
        assert any("cardio" in tid.lower() or "heart" in tid.lower() for tid in topic_ids), (
            f"CHF should map to cardiovascular topics, got: {topic_ids}"
        )

    def test_matches_dvt_to_hematology(self, sample_dvt_chunk, mock_taxonomy_service, mock_vector_store):
        """DVT abbreviation maps to coagulation/hematology topics."""
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "hematology_coagulation", "score": 0.85},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_dvt_chunk)

        topic_ids = [r.topic_id for r in results]
        assert any("hematology" in tid.lower() or "coagulation" in tid.lower() for tid in topic_ids), (
            f"DVT should map to hematology/coagulation topics, got: {topic_ids}"
        )

    def test_hybrid_search_catches_abbreviations(self, sample_chf_chunk, mock_taxonomy_service, mock_vector_store):
        """BM25 component of hybrid search catches abbreviations."""
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        service.classify(sample_chf_chunk)

        mock_vector_store.hybrid_search.assert_called()
        call_args = mock_vector_store.hybrid_search.call_args
        assert call_args is not None
        assert 'alpha' in call_args.kwargs or len(call_args.args) >= 2


class TestDualTaxonomy:
    """Tests for dual taxonomy classification (MCAT/USMLE)."""

    def test_classifies_against_mcat(self, sample_biochemistry_chunk, mock_taxonomy_service, mock_vector_store):
        """Returns MCAT topic classifications."""
        mock_taxonomy_service.get_taxonomy.return_value = {
            "exam_type": "mcat",
            "topics": [{"id": "mcat_biochem_001", "name": "Amino Acids"}]
        }
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "mcat_biochem_001", "score": 0.87},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_biochemistry_chunk, exam_type="mcat")

        assert any("mcat" in r.topic_id.lower() for r in results), (
            "Should return MCAT-specific topics"
        )

    def test_classifies_against_usmle(self, sample_biochemistry_chunk, mock_taxonomy_service, mock_vector_store):
        """Returns USMLE topic classifications."""
        mock_taxonomy_service.get_taxonomy.return_value = {
            "exam_type": "usmle",
            "topics": [{"id": "usmle_biochem_001", "name": "Amino Acids"}]
        }
        mock_vector_store.hybrid_search.return_value = [
            {"topic_id": "usmle_biochem_001", "score": 0.89},
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        results = service.classify(sample_biochemistry_chunk, exam_type="usmle")

        assert any("usmle" in r.topic_id.lower() for r in results), (
            "Should return USMLE-specific topics"
        )

    def test_detects_primary_exam(self, sample_biochemistry_chunk, mock_taxonomy_service, mock_vector_store):
        """Determines best-fit exam type for the content."""
        mock_vector_store.hybrid_search.side_effect = [
            [{"topic_id": "mcat_biochem_001", "score": 0.75}],
            [{"topic_id": "usmle_biochem_001", "score": 0.88}],
        ]
        service = ClassificationService(
            taxonomy_service=mock_taxonomy_service,
            vector_store=mock_vector_store
        )
        primary_exam = service.detect_primary_exam(sample_biochemistry_chunk)

        assert primary_exam in ["mcat", "usmle"], f"Primary exam should be mcat or usmle, got: {primary_exam}"
