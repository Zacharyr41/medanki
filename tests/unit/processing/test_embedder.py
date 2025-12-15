from __future__ import annotations

import numpy as np
import pytest

from medanki.processing.embedder import EmbeddingService


class TestBasicEmbedding:
    @pytest.mark.asyncio
    async def test_embed_single_text(self, mock_embedder: EmbeddingService) -> None:
        result = await mock_embedder.embed("congestive heart failure")
        assert isinstance(result, list)
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_embedder: EmbeddingService) -> None:
        texts = ["heart failure", "myocardial infarction", "atrial fibrillation"]
        results = await mock_embedder.embed_batch(texts)
        assert len(results) == 3
        assert all(len(v) == 768 for v in results)

    @pytest.mark.asyncio
    async def test_embedding_is_normalized(self, mock_embedder: EmbeddingService) -> None:
        result = await mock_embedder.embed("test text")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-5

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, mock_embedder: EmbeddingService) -> None:
        with pytest.raises(ValueError, match="empty"):
            await mock_embedder.embed("")

    @pytest.mark.asyncio
    async def test_embedding_is_deterministic(self, mock_embedder: EmbeddingService) -> None:
        text = "deterministic test"
        result1 = await mock_embedder.embed(text)
        result2 = await mock_embedder.embed(text)
        assert result1 == result2


class TestMedicalDomain:
    @pytest.mark.asyncio
    async def test_medical_terms_similar(self, real_embedder: EmbeddingService) -> None:
        chf_embedding = await real_embedder.embed("CHF")
        heart_failure_embedding = await real_embedder.embed("heart failure")
        similarity = np.dot(chf_embedding, heart_failure_embedding)
        assert similarity > 0.7

    @pytest.mark.asyncio
    async def test_unrelated_terms_distant(self, real_embedder: EmbeddingService) -> None:
        chf_embedding = await real_embedder.embed("CHF")
        fracture_embedding = await real_embedder.embed("tibial fracture")
        similarity = np.dot(chf_embedding, fracture_embedding)
        assert similarity < 0.5


class TestCaching:
    @pytest.mark.asyncio
    async def test_uses_cache_for_repeated_text(
        self, mock_embedder_with_cache: EmbeddingService, mock_cache: dict
    ) -> None:
        text = "cache test"
        await mock_embedder_with_cache.embed(text)
        await mock_embedder_with_cache.embed(text)
        assert mock_cache["hit_count"] == 1

    @pytest.mark.asyncio
    async def test_cache_key_is_content_hash(
        self, mock_embedder_with_cache: EmbeddingService, mock_cache: dict
    ) -> None:
        await mock_embedder_with_cache.embed("test content")
        keys = list(mock_cache["data"].keys())
        assert len(keys) == 1
        assert len(keys[0]) == 64  # SHA-256 hex digest


class TestLongTextHandling:
    """Tests for handling long text input."""

    @pytest.mark.asyncio
    async def test_embed_handles_long_text(self, mock_embedder: EmbeddingService) -> None:
        """Long texts are handled (truncated or chunked internally)."""
        long_text = " ".join(["medical term"] * 1000)
        result = await mock_embedder.embed(long_text)

        assert len(result) == 768
        assert any(v != 0 for v in result)
