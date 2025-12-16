"""Feedback service for quality improvement and classification training."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from medanki.models.feedback import (
    CardFeedback,
    FeedbackAggregate,
    FeedbackCategory,
    FeedbackType,
    ImplicitSignal,
    TaxonomyCorrection,
)
from medanki.storage.feedback_repository import FeedbackRepository


@runtime_checkable
class IEmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass
class FeedbackStats:
    total_feedback: int
    positive_count: int
    negative_count: int
    approval_rate: float
    total_corrections: int
    top_correction_patterns: list[dict]


class FeedbackService:
    def __init__(
        self,
        db_path: Path | str,
        embedding_client: IEmbeddingClient | None = None,
    ):
        self._repo = FeedbackRepository(db_path)
        self._embedding_client = embedding_client
        self._initialized = False

    async def initialize(self) -> None:
        if not self._initialized:
            await self._repo.initialize()
            self._initialized = True

    async def close(self) -> None:
        await self._repo.close()

    async def __aenter__(self) -> FeedbackService:
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def submit_feedback(
        self,
        card_id: UUID,
        user_id: str,
        feedback_type: FeedbackType,
        categories: list[FeedbackCategory] | None = None,
        comment: str | None = None,
        card_text: str | None = None,
        topic_id: str | None = None,
    ) -> CardFeedback:
        await self.initialize()

        feedback = CardFeedback(
            card_id=card_id,
            user_id=user_id,
            feedback_type=feedback_type,
            categories=categories or [],
            comment=comment,
        )

        await self._repo.insert_feedback(feedback)

        if (
            self._embedding_client
            and card_text
            and topic_id
            and feedback_type in (FeedbackType.THUMBS_UP, FeedbackType.THUMBS_DOWN)
        ):
            embedding = await self._embedding_client.embed(card_text)
            is_positive = feedback_type == FeedbackType.THUMBS_UP
            await self._repo.store_feedback_embedding(
                card_id, topic_id, embedding, is_positive
            )

        return feedback

    async def submit_correction(
        self,
        card_id: UUID,
        user_id: str,
        original_topic_id: str,
        corrected_topic_id: str,
        confidence: float = 1.0,
        comment: str | None = None,
    ) -> TaxonomyCorrection:
        await self.initialize()

        correction = TaxonomyCorrection(
            card_id=card_id,
            user_id=user_id,
            original_topic_id=original_topic_id,
            corrected_topic_id=corrected_topic_id,
            confidence=confidence,
            comment=comment,
        )

        await self._repo.insert_correction(correction)
        return correction

    async def submit_implicit_signal(
        self,
        card_id: UUID,
        user_id: str,
        view_time_ms: int = 0,
        flip_count: int = 0,
        scroll_depth: float = 0.0,
        edit_attempted: bool = False,
        copy_attempted: bool = False,
        skipped: bool = False,
    ) -> ImplicitSignal:
        await self.initialize()

        signal = ImplicitSignal(
            card_id=card_id,
            user_id=user_id,
            view_time_ms=view_time_ms,
            flip_count=flip_count,
            scroll_depth=scroll_depth,
            edit_attempted=edit_attempted,
            copy_attempted=copy_attempted,
            skipped=skipped,
        )

        await self._repo.insert_implicit_signal(signal)
        return signal

    async def get_card_feedback(self, card_id: UUID) -> list[CardFeedback]:
        await self.initialize()
        return await self._repo.get_feedback_for_card(card_id)

    async def get_card_aggregate(self, card_id: UUID) -> FeedbackAggregate:
        await self.initialize()
        return await self._repo.get_aggregate(card_id)

    async def get_cards_needing_review(
        self,
        min_feedback: int = 5,
        max_approval_rate: float = 0.4,
    ) -> list[UUID]:
        await self.initialize()
        return await self._repo.get_low_quality_cards(min_feedback, max_approval_rate)

    async def get_high_quality_cards(
        self,
        min_feedback: int = 3,
        min_approval_rate: float = 0.8,
    ) -> list[UUID]:
        await self.initialize()
        return await self._repo.get_high_quality_cards(min_feedback, min_approval_rate)

    async def get_correction_patterns(self) -> list[dict]:
        await self.initialize()
        return await self._repo.get_correction_patterns()

    async def get_positive_embeddings_for_topic(
        self, topic_id: str
    ) -> list[list[float]]:
        await self.initialize()
        return await self._repo.get_positive_embeddings(topic_id)

    async def get_negative_embeddings_for_topic(
        self, topic_id: str
    ) -> list[list[float]]:
        await self.initialize()
        return await self._repo.get_negative_embeddings(topic_id)

    async def get_stats(self) -> FeedbackStats:
        await self.initialize()
        conn = await self._repo._get_connection()

        cursor = await conn.execute(
            """SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as positive,
                 SUM(CASE WHEN feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as negative
               FROM card_feedback"""
        )
        row = await cursor.fetchone()
        total = row["total"] or 0
        positive = row["positive"] or 0
        negative = row["negative"] or 0
        approval_rate = positive / total if total > 0 else 0.0

        cursor = await conn.execute("SELECT COUNT(*) as count FROM taxonomy_corrections")
        row = await cursor.fetchone()
        total_corrections = row["count"] or 0

        patterns = await self._repo.get_correction_patterns()

        return FeedbackStats(
            total_feedback=total,
            positive_count=positive,
            negative_count=negative,
            approval_rate=approval_rate,
            total_corrections=total_corrections,
            top_correction_patterns=patterns[:10],
        )

    async def update_daily_metrics(self, for_date: date | None = None) -> None:
        await self.initialize()
        await self._repo.update_daily_metrics(for_date)

    async def export_training_data(
        self,
        output_path: Path,
        include_positive: bool = True,
        include_negative: bool = True,
        min_feedback: int = 3,
    ) -> int:
        await self.initialize()

        positive_cards = []
        negative_cards = []

        if include_positive:
            positive_cards = await self._repo.get_high_quality_cards(min_feedback, 0.8)

        if include_negative:
            negative_cards = await self._repo.get_low_quality_cards(min_feedback, 0.4)

        import json

        import aiofiles

        data = []
        for card_id in positive_cards:
            data.append({"card_id": str(card_id), "label": "positive"})
        for card_id in negative_cards:
            data.append({"card_id": str(card_id), "label": "negative"})

        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(output_path, "w") as f:
            for item in data:
                await f.write(json.dumps(item) + "\n")

        return len(data)

    async def compute_positive_centroid(self, topic_id: str) -> list[float] | None:
        await self.initialize()
        embeddings = await self._repo.get_positive_embeddings(topic_id)

        if not embeddings:
            return None

        import numpy as np

        arr = np.array(embeddings)
        centroid = np.mean(arr, axis=0)

        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        return centroid.tolist()

    async def compute_negative_centroid(self, topic_id: str) -> list[float] | None:
        await self.initialize()
        embeddings = await self._repo.get_negative_embeddings(topic_id)

        if not embeddings:
            return None

        import numpy as np

        arr = np.array(embeddings)
        centroid = np.mean(arr, axis=0)

        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        return centroid.tolist()
