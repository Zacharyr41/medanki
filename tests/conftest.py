from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def sample_medical_terms() -> list[str]:
    return [
        "congestive heart failure",
        "myocardial infarction",
        "atrial fibrillation",
        "chronic obstructive pulmonary disease",
        "diabetes mellitus type 2",
        "hypertension",
        "acute kidney injury",
        "pneumonia",
    ]


@pytest.fixture
def mock_cache() -> dict:
    return {"data": {}, "hit_count": 0}


def _generate_deterministic_embedding(text: str, dim: int = 768) -> list[float]:
    seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    vec = rng.random(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


@pytest.fixture
def mock_embedder() -> Generator:
    with patch("medanki.processing.embedder.SentenceTransformer") as mock_st:
        mock_model = MagicMock()

        def encode_fn(texts, normalize_embeddings=True, batch_size=32, **kwargs):
            if isinstance(texts, str):
                texts = [texts]
            results = []
            for t in texts:
                results.append(_generate_deterministic_embedding(t))
            return np.array(results)

        mock_model.encode = encode_fn
        mock_st.return_value = mock_model

        from medanki.processing.embedder import EmbeddingService

        yield EmbeddingService()


@pytest.fixture
def mock_embedder_with_cache(mock_cache: dict) -> Generator:
    with patch("medanki.processing.embedder.SentenceTransformer") as mock_st:
        mock_model = MagicMock()

        def encode_fn(texts, normalize_embeddings=True, batch_size=32, **kwargs):
            if isinstance(texts, str):
                texts = [texts]
            results = []
            for t in texts:
                results.append(_generate_deterministic_embedding(t))
            return np.array(results)

        mock_model.encode = encode_fn
        mock_st.return_value = mock_model

        from medanki.processing.embedder import EmbeddingService

        class MockCacheService:
            async def get(self, key: str):
                if key in mock_cache["data"]:
                    mock_cache["hit_count"] += 1
                    return mock_cache["data"][key]
                return None

            async def set(self, key: str, value: list[float], ttl: int | None = None):
                mock_cache["data"][key] = value

        service = EmbeddingService(cache=MockCacheService())
        yield service


@pytest.fixture
def real_embedder() -> Generator:
    pytest.importorskip("sentence_transformers")
    from medanki.processing.embedder import EmbeddingService

    yield EmbeddingService()
