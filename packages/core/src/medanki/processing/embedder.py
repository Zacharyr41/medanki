from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Protocol, cast

import torch
from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from collections.abc import Sequence


class ICacheService(Protocol):
    async def get(self, key: str) -> list[float] | None: ...
    async def set(self, key: str, value: list[float], ttl: int | None = None) -> None: ...


class EmbeddingService:
    DEFAULT_MODEL = "neuml/pubmedbert-base-embeddings"
    EMBEDDING_DIM = 768

    def __init__(
        self,
        model_name: str | None = None,
        cache: ICacheService | None = None,
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name or self.DEFAULT_MODEL
        self._cache = cache
        self._batch_size = batch_size
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = SentenceTransformer(self._model_name, device=self._device)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        return self.EMBEDDING_DIM

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    async def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        cache_key = self._hash_text(text)

        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached

        embeddings = self._model.encode(
            [text],
            normalize_embeddings=True,
            batch_size=self._batch_size,
        )
        result: list[float] = cast(list[float], embeddings[0].tolist())

        if self._cache is not None:
            await self._cache.set(cache_key, result)

        return result

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        for text in texts:
            if not text or not text.strip():
                raise ValueError("Cannot embed empty text")

        results: list[list[float] | None] = [None] * len(texts)
        texts_to_embed: list[tuple[int, str]] = []

        if self._cache is not None:
            for i, text in enumerate(texts):
                cache_key = self._hash_text(text)
                cached = await self._cache.get(cache_key)
                if cached is not None:
                    results[i] = cached
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))

        if texts_to_embed:
            indices, uncached_texts = zip(*texts_to_embed, strict=True)
            embeddings = self._model.encode(
                list(uncached_texts),
                normalize_embeddings=True,
                batch_size=self._batch_size,
            )

            for idx, embedding in zip(indices, embeddings, strict=True):
                result = embedding.tolist()
                results[idx] = result
                if self._cache is not None:
                    await self._cache.set(self._hash_text(texts[idx]), result)

        return [r for r in results if r is not None]
