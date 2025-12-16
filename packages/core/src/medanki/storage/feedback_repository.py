"""Feedback repository for card quality and taxonomy correction tracking."""

from __future__ import annotations

import struct
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import aiosqlite

from medanki.models.feedback import (
    CardFeedback,
    FeedbackAggregate,
    FeedbackCategory,
    FeedbackType,
    ImplicitSignal,
    TaxonomyCorrection,
)


class FeedbackRepository:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    async def initialize(self) -> None:
        conn = await self._get_connection()
        schema_path = Path(__file__).parent / "feedback_schema.sql"
        await conn.executescript(schema_path.read_text())
        await conn.commit()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def insert_feedback(self, feedback: CardFeedback) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """INSERT INTO card_feedback (id, card_id, user_id, feedback_type, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(feedback.id),
                str(feedback.card_id),
                feedback.user_id,
                feedback.feedback_type.value,
                feedback.comment,
                feedback.created_at.isoformat(),
            ),
        )
        if feedback.categories:
            await conn.executemany(
                "INSERT INTO feedback_categories (feedback_id, category) VALUES (?, ?)",
                [(str(feedback.id), cat.value) for cat in feedback.categories],
            )
        await conn.commit()
        return str(feedback.id)

    async def get_feedback(self, feedback_id: str) -> CardFeedback | None:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM card_feedback WHERE id = ?", (feedback_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        cat_cursor = await conn.execute(
            "SELECT category FROM feedback_categories WHERE feedback_id = ?",
            (feedback_id,),
        )
        cat_rows = await cat_cursor.fetchall()
        categories = [FeedbackCategory(r["category"]) for r in cat_rows]

        return CardFeedback(
            id=UUID(row["id"]),
            card_id=UUID(row["card_id"]),
            user_id=row["user_id"],
            feedback_type=FeedbackType(row["feedback_type"]),
            categories=categories,
            comment=row["comment"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def get_feedback_for_card(self, card_id: UUID) -> list[CardFeedback]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM card_feedback WHERE card_id = ? ORDER BY created_at DESC",
            (str(card_id),),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            cat_cursor = await conn.execute(
                "SELECT category FROM feedback_categories WHERE feedback_id = ?",
                (row["id"],),
            )
            cat_rows = await cat_cursor.fetchall()
            categories = [FeedbackCategory(r["category"]) for r in cat_rows]
            results.append(
                CardFeedback(
                    id=UUID(row["id"]),
                    card_id=UUID(row["card_id"]),
                    user_id=row["user_id"],
                    feedback_type=FeedbackType(row["feedback_type"]),
                    categories=categories,
                    comment=row["comment"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return results

    async def insert_correction(self, correction: TaxonomyCorrection) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """INSERT INTO taxonomy_corrections
               (id, card_id, user_id, original_topic_id, corrected_topic_id, confidence, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(correction.id),
                str(correction.card_id),
                correction.user_id,
                correction.original_topic_id,
                correction.corrected_topic_id,
                correction.confidence,
                correction.comment,
                correction.created_at.isoformat(),
            ),
        )
        await conn.commit()
        return str(correction.id)

    async def get_corrections_for_card(self, card_id: UUID) -> list[TaxonomyCorrection]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM taxonomy_corrections WHERE card_id = ? ORDER BY created_at DESC",
            (str(card_id),),
        )
        rows = await cursor.fetchall()
        return [
            TaxonomyCorrection(
                id=UUID(row["id"]),
                card_id=UUID(row["card_id"]),
                user_id=row["user_id"],
                original_topic_id=row["original_topic_id"],
                corrected_topic_id=row["corrected_topic_id"],
                confidence=row["confidence"],
                comment=row["comment"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def get_corrections_by_topic(
        self, topic_id: str, as_original: bool = True
    ) -> list[TaxonomyCorrection]:
        conn = await self._get_connection()
        column = "original_topic_id" if as_original else "corrected_topic_id"
        cursor = await conn.execute(
            f"SELECT * FROM taxonomy_corrections WHERE {column} = ? ORDER BY created_at DESC",
            (topic_id,),
        )
        rows = await cursor.fetchall()
        return [
            TaxonomyCorrection(
                id=UUID(row["id"]),
                card_id=UUID(row["card_id"]),
                user_id=row["user_id"],
                original_topic_id=row["original_topic_id"],
                corrected_topic_id=row["corrected_topic_id"],
                confidence=row["confidence"],
                comment=row["comment"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def insert_implicit_signal(self, signal: ImplicitSignal) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """INSERT INTO implicit_signals
               (id, card_id, user_id, view_time_ms, flip_count, scroll_depth,
                edit_attempted, copy_attempted, skipped, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(signal.id),
                str(signal.card_id),
                signal.user_id,
                signal.view_time_ms,
                signal.flip_count,
                signal.scroll_depth,
                signal.edit_attempted,
                signal.copy_attempted,
                signal.skipped,
                signal.created_at.isoformat(),
            ),
        )
        await conn.commit()
        return str(signal.id)

    async def get_signals_for_card(self, card_id: UUID) -> list[ImplicitSignal]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM implicit_signals WHERE card_id = ? ORDER BY created_at DESC",
            (str(card_id),),
        )
        rows = await cursor.fetchall()
        return [
            ImplicitSignal(
                id=UUID(row["id"]),
                card_id=UUID(row["card_id"]),
                user_id=row["user_id"],
                view_time_ms=row["view_time_ms"],
                flip_count=row["flip_count"],
                scroll_depth=row["scroll_depth"],
                edit_attempted=bool(row["edit_attempted"]),
                copy_attempted=bool(row["copy_attempted"]),
                skipped=bool(row["skipped"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def store_feedback_embedding(
        self,
        card_id: UUID,
        topic_id: str,
        embedding: list[float],
        is_positive: bool,
    ) -> int:
        conn = await self._get_connection()
        embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)
        cursor = await conn.execute(
            """INSERT OR REPLACE INTO feedback_embeddings
               (card_id, topic_id, embedding, is_positive, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(card_id),
                topic_id,
                embedding_blob,
                is_positive,
                datetime.utcnow().isoformat(),
            ),
        )
        await conn.commit()
        return cursor.lastrowid or 0

    async def get_positive_embeddings(self, topic_id: str) -> list[list[float]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT embedding FROM feedback_embeddings WHERE topic_id = ? AND is_positive = TRUE",
            (topic_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            blob = row["embedding"]
            count = len(blob) // 4
            embedding = list(struct.unpack(f"{count}f", blob))
            results.append(embedding)
        return results

    async def get_negative_embeddings(self, topic_id: str) -> list[list[float]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT embedding FROM feedback_embeddings WHERE topic_id = ? AND is_positive = FALSE",
            (topic_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            blob = row["embedding"]
            count = len(blob) // 4
            embedding = list(struct.unpack(f"{count}f", blob))
            results.append(embedding)
        return results

    async def get_aggregate(self, card_id: UUID) -> FeedbackAggregate:
        conn = await self._get_connection()

        cursor = await conn.execute(
            """SELECT
                 SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as up,
                 SUM(CASE WHEN feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as down
               FROM card_feedback WHERE card_id = ?""",
            (str(card_id),),
        )
        row = await cursor.fetchone()
        thumbs_up = row["up"] or 0
        thumbs_down = row["down"] or 0

        cursor = await conn.execute(
            "SELECT AVG(view_time_ms) as avg_time FROM implicit_signals WHERE card_id = ?",
            (str(card_id),),
        )
        row = await cursor.fetchone()
        avg_view_time = row["avg_time"] or 0.0

        cursor = await conn.execute(
            "SELECT COUNT(*) as count FROM taxonomy_corrections WHERE card_id = ?",
            (str(card_id),),
        )
        row = await cursor.fetchone()
        correction_count = row["count"] or 0

        cursor = await conn.execute(
            """SELECT fc.category, COUNT(*) as count
               FROM feedback_categories fc
               JOIN card_feedback cf ON fc.feedback_id = cf.id
               WHERE cf.card_id = ?
               GROUP BY fc.category
               ORDER BY count DESC
               LIMIT 3""",
            (str(card_id),),
        )
        cat_rows = await cursor.fetchall()
        categories = [FeedbackCategory(r["category"]) for r in cat_rows]

        return FeedbackAggregate(
            card_id=card_id,
            total_thumbs_up=thumbs_up,
            total_thumbs_down=thumbs_down,
            avg_view_time_ms=avg_view_time,
            correction_count=correction_count,
            most_common_categories=categories,
        )

    async def update_daily_metrics(self, for_date: date | None = None) -> None:
        conn = await self._get_connection()
        target_date = (for_date or date.today()).isoformat()

        await conn.execute(
            """INSERT OR REPLACE INTO quality_metrics_daily
               (date, topic_id, total_cards, thumbs_up_count, thumbs_down_count, correction_count, avg_view_time_ms)
               SELECT
                 DATE(cf.created_at) as date,
                 NULL as topic_id,
                 COUNT(DISTINCT cf.card_id) as total_cards,
                 SUM(CASE WHEN cf.feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up_count,
                 SUM(CASE WHEN cf.feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down_count,
                 0 as correction_count,
                 0.0 as avg_view_time_ms
               FROM card_feedback cf
               WHERE DATE(cf.created_at) = ?
               GROUP BY DATE(cf.created_at)""",
            (target_date,),
        )
        await conn.commit()

    async def get_low_quality_cards(
        self, min_feedback: int = 5, max_approval_rate: float = 0.4
    ) -> list[UUID]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT card_id,
                 SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as up,
                 SUM(CASE WHEN feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as down,
                 COUNT(*) as total
               FROM card_feedback
               GROUP BY card_id
               HAVING total >= ? AND (CAST(up AS REAL) / total) <= ?""",
            (min_feedback, max_approval_rate),
        )
        rows = await cursor.fetchall()
        return [UUID(row["card_id"]) for row in rows]

    async def get_high_quality_cards(
        self, min_feedback: int = 3, min_approval_rate: float = 0.8
    ) -> list[UUID]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT card_id,
                 SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as up,
                 COUNT(*) as total
               FROM card_feedback
               GROUP BY card_id
               HAVING total >= ? AND (CAST(up AS REAL) / total) >= ?""",
            (min_feedback, min_approval_rate),
        )
        rows = await cursor.fetchall()
        return [UUID(row["card_id"]) for row in rows]

    async def get_correction_patterns(self) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT original_topic_id, corrected_topic_id, COUNT(*) as count
               FROM taxonomy_corrections
               GROUP BY original_topic_id, corrected_topic_id
               ORDER BY count DESC
               LIMIT 50"""
        )
        rows = await cursor.fetchall()
        return [
            {
                "original_topic_id": row["original_topic_id"],
                "corrected_topic_id": row["corrected_topic_id"],
                "count": row["count"],
            }
            for row in rows
        ]

    async def get_all_topic_ids_with_feedback(self) -> list[str]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT DISTINCT topic_id FROM feedback_embeddings"
        )
        rows = await cursor.fetchall()
        return [row["topic_id"] for row in rows]
