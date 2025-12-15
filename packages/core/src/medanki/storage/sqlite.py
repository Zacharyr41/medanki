from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from .models import JobStatus


class SQLiteStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def initialize(self) -> None:
        conn = await self._get_connection()
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                content_type TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                text TEXT NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                token_count INTEGER NOT NULL,
                section_path TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                card_type TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                google_id TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                picture_url TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_login TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS saved_cards (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                saved_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, card_id)
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_cards_document ON cards(document_id);
            CREATE INDEX IF NOT EXISTS idx_cards_content_hash ON cards(content_hash);
            CREATE INDEX IF NOT EXISTS idx_jobs_document ON jobs(document_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
            CREATE INDEX IF NOT EXISTS idx_saved_cards_user ON saved_cards(user_id);

            PRAGMA foreign_keys = ON;
        """)
        await conn.commit()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _get_tables(self) -> list[str]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def _get_table_columns(self, table: str) -> list[str]:
        conn = await self._get_connection()
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        return [row[1] for row in rows]

    async def insert_document(
        self,
        id: str,
        source_path: str,
        content_type: str,
        raw_text: str,
        metadata: dict[str, Any]
    ) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """
            INSERT INTO documents (id, source_path, content_type, raw_text, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (id, source_path, content_type, raw_text, json.dumps(metadata), datetime.utcnow().isoformat())
        )
        await conn.commit()
        return id

    async def get_document(self, id: str) -> dict[str, Any] | None:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM documents WHERE id = ?", (id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "source_path": row["source_path"],
            "content_type": row["content_type"],
            "raw_text": row["raw_text"],
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
        }

    async def list_documents(self) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM documents ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "source_path": row["source_path"],
                "content_type": row["content_type"],
                "raw_text": row["raw_text"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def delete_document(self, id: str) -> None:
        conn = await self._get_connection()
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("DELETE FROM cards WHERE document_id = ?", (id,))
        await conn.execute("DELETE FROM chunks WHERE document_id = ?", (id,))
        await conn.execute("DELETE FROM documents WHERE id = ?", (id,))
        await conn.commit()

    async def insert_chunk(
        self,
        id: str,
        document_id: str,
        text: str,
        start_char: int,
        end_char: int,
        token_count: int,
        section_path: list[str]
    ) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """
            INSERT INTO chunks (id, document_id, text, start_char, end_char, token_count, section_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (id, document_id, text, start_char, end_char, token_count, json.dumps(section_path))
        )
        await conn.commit()
        return id

    async def get_chunks_by_document(self, document_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM chunks WHERE document_id = ?", (document_id,))
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "text": row["text"],
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "token_count": row["token_count"],
                "section_path": json.loads(row["section_path"]),
            }
            for row in rows
        ]

    async def insert_card(
        self,
        id: str,
        document_id: str,
        chunk_id: str,
        card_type: str,
        content: str,
        tags: list[str],
        status: str = "pending"
    ) -> str:
        conn = await self._get_connection()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        await conn.execute(
            """
            INSERT INTO cards (id, document_id, chunk_id, card_type, content, content_hash, tags, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, document_id, chunk_id, card_type, content, content_hash, json.dumps(tags), status, datetime.utcnow().isoformat())
        )
        await conn.commit()
        return id

    async def get_cards_by_document(self, document_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM cards WHERE document_id = ?", (document_id,))
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "chunk_id": row["chunk_id"],
                "card_type": row["card_type"],
                "content": row["content"],
                "content_hash": row["content_hash"],
                "tags": json.loads(row["tags"]),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def get_cards_by_topic(self, topic: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM cards")
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            tags = json.loads(row["tags"])
            if topic in tags:
                result.append({
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_id": row["chunk_id"],
                    "card_type": row["card_type"],
                    "content": row["content"],
                    "content_hash": row["content_hash"],
                    "tags": tags,
                    "status": row["status"],
                    "created_at": row["created_at"],
                })
        return result

    async def update_card_status(self, card_id: str, status: str) -> None:
        conn = await self._get_connection()
        await conn.execute("UPDATE cards SET status = ? WHERE id = ?", (status, card_id))
        await conn.commit()

    async def create_job(self, id: str, document_id: str) -> str:
        conn = await self._get_connection()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            """
            INSERT INTO jobs (id, document_id, status, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (id, document_id, JobStatus.PENDING.value, 0, now, now)
        )
        await conn.commit()
        return id

    async def get_job(self, id: str) -> dict[str, Any] | None:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM jobs WHERE id = ?", (id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "document_id": row["document_id"],
            "status": row["status"],
            "progress": row["progress"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def update_job_status(self, job_id: str, status: JobStatus) -> None:
        conn = await self._get_connection()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, job_id)
        )
        await conn.commit()

    async def update_job_progress(self, job_id: str, progress: int) -> None:
        conn = await self._get_connection()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            "UPDATE jobs SET progress = ?, updated_at = ? WHERE id = ?",
            (progress, now, job_id)
        )
        await conn.commit()

    async def set_job_error(self, job_id: str, error: str) -> None:
        conn = await self._get_connection()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            "UPDATE jobs SET error = ?, status = ?, updated_at = ? WHERE id = ?",
            (error, JobStatus.FAILED.value, now, job_id)
        )
        await conn.commit()

    async def list_recent_jobs(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "status": row["status"],
                "progress": row["progress"],
                "error": row["error"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
