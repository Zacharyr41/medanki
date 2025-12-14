"""Tests for SQLite storage and job tracking."""

from __future__ import annotations

import sys
sys.path.insert(0, "/Users/zacharyrothstein/Code/medanki-tests/packages/core/src")

import asyncio
import hashlib
import tempfile
from pathlib import Path

import pytest

from medanki.storage.sqlite import SQLiteStore
from medanki.storage.models import JobStatus, Job


class TestSchemaCreation:
    """Tests for database schema creation."""

    @pytest.fixture
    def db_path(self, tmp_path):
        return tmp_path / "test.db"

    @pytest.fixture
    def store(self, db_path):
        s = SQLiteStore(db_path)
        asyncio.run(s.initialize())
        yield s
        asyncio.run(s.close())

    def test_creates_tables_on_init(self, store):
        """Tables created automatically on initialization."""
        tables = asyncio.run(store._get_tables())
        assert "documents" in tables
        assert "chunks" in tables
        assert "cards" in tables
        assert "jobs" in tables

    def test_documents_table_exists(self, store):
        """Documents table has correct schema."""
        columns = asyncio.run(store._get_table_columns("documents"))
        assert "id" in columns
        assert "source_path" in columns
        assert "content_type" in columns
        assert "raw_text" in columns
        assert "metadata" in columns
        assert "created_at" in columns

    def test_chunks_table_exists(self, store):
        """Chunks table has correct schema."""
        columns = asyncio.run(store._get_table_columns("chunks"))
        assert "id" in columns
        assert "document_id" in columns
        assert "text" in columns
        assert "start_char" in columns
        assert "end_char" in columns
        assert "token_count" in columns
        assert "section_path" in columns

    def test_cards_table_exists(self, store):
        """Cards table has correct schema."""
        columns = asyncio.run(store._get_table_columns("cards"))
        assert "id" in columns
        assert "document_id" in columns
        assert "chunk_id" in columns
        assert "card_type" in columns
        assert "content" in columns
        assert "content_hash" in columns
        assert "tags" in columns
        assert "status" in columns

    def test_jobs_table_exists(self, store):
        """Jobs table has correct schema."""
        columns = asyncio.run(store._get_table_columns("jobs"))
        assert "id" in columns
        assert "document_id" in columns
        assert "status" in columns
        assert "progress" in columns
        assert "error" in columns
        assert "created_at" in columns
        assert "updated_at" in columns


class TestDocumentCRUD:
    """Tests for document CRUD operations."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test.db"
        s = SQLiteStore(db_path)
        asyncio.run(s.initialize())
        yield s
        asyncio.run(s.close())

    def test_insert_document(self, store):
        """Creates document record."""
        doc_id = asyncio.run(store.insert_document(
            id="doc_001",
            source_path="/path/to/file.pdf",
            content_type="pdf_textbook",
            raw_text="Sample medical content.",
            metadata={"page_count": 10}
        ))

        assert doc_id == "doc_001"

    def test_get_document_by_id(self, store):
        """Retrieves document by ID."""
        asyncio.run(store.insert_document(
            id="doc_002",
            source_path="/path/to/file.pdf",
            content_type="pdf_textbook",
            raw_text="Medical content here.",
            metadata={"page_count": 5}
        ))

        doc = asyncio.run(store.get_document("doc_002"))

        assert doc is not None
        assert doc["id"] == "doc_002"
        assert doc["source_path"] == "/path/to/file.pdf"
        assert doc["raw_text"] == "Medical content here."

    def test_list_documents(self, store):
        """Lists all documents."""
        asyncio.run(store.insert_document(
            id="doc_a",
            source_path="/a.pdf",
            content_type="pdf_textbook",
            raw_text="Content A",
            metadata={}
        ))
        asyncio.run(store.insert_document(
            id="doc_b",
            source_path="/b.pdf",
            content_type="pdf_slides",
            raw_text="Content B",
            metadata={}
        ))

        docs = asyncio.run(store.list_documents())

        assert len(docs) == 2
        doc_ids = {d["id"] for d in docs}
        assert "doc_a" in doc_ids
        assert "doc_b" in doc_ids

    def test_delete_document_cascades(self, store):
        """Deleting document cascades to related chunks and cards."""
        asyncio.run(store.insert_document(
            id="doc_cascade",
            source_path="/cascade.pdf",
            content_type="pdf_textbook",
            raw_text="Cascade test content",
            metadata={}
        ))
        asyncio.run(store.insert_chunk(
            id="chunk_cascade",
            document_id="doc_cascade",
            text="Chunk text",
            start_char=0,
            end_char=10,
            token_count=5,
            section_path=[]
        ))
        asyncio.run(store.insert_card(
            id="card_cascade",
            document_id="doc_cascade",
            chunk_id="chunk_cascade",
            card_type="cloze",
            content="{{c1::test}}",
            tags=["test"]
        ))

        asyncio.run(store.delete_document("doc_cascade"))

        doc = asyncio.run(store.get_document("doc_cascade"))
        chunks = asyncio.run(store.get_chunks_by_document("doc_cascade"))
        cards = asyncio.run(store.get_cards_by_document("doc_cascade"))

        assert doc is None
        assert len(chunks) == 0
        assert len(cards) == 0


class TestCardCRUD:
    """Tests for card CRUD operations."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test.db"
        s = SQLiteStore(db_path)
        asyncio.run(s.initialize())
        asyncio.run(s.insert_document(
            id="doc_cards",
            source_path="/cards.pdf",
            content_type="pdf_textbook",
            raw_text="Cards test content",
            metadata={}
        ))
        asyncio.run(s.insert_chunk(
            id="chunk_cards",
            document_id="doc_cards",
            text="Chunk for cards",
            start_char=0,
            end_char=15,
            token_count=3,
            section_path=["Section1"]
        ))
        yield s
        asyncio.run(s.close())

    def test_insert_card(self, store):
        """Creates card record."""
        card_id = asyncio.run(store.insert_card(
            id="card_001",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="cloze",
            content="The heart has {{c1::four}} chambers.",
            tags=["cardiology", "anatomy"]
        ))

        assert card_id == "card_001"

    def test_get_cards_by_document(self, store):
        """Filters cards by document."""
        asyncio.run(store.insert_card(
            id="card_doc_1",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="cloze",
            content="Card 1 content",
            tags=["tag1"]
        ))
        asyncio.run(store.insert_card(
            id="card_doc_2",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="vignette",
            content="Card 2 content",
            tags=["tag2"]
        ))

        cards = asyncio.run(store.get_cards_by_document("doc_cards"))

        assert len(cards) == 2

    def test_get_cards_by_topic(self, store):
        """Filters cards by topic tag."""
        asyncio.run(store.insert_card(
            id="card_topic_1",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="cloze",
            content="Cardiology content",
            tags=["cardiology", "physiology"]
        ))
        asyncio.run(store.insert_card(
            id="card_topic_2",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="cloze",
            content="Neurology content",
            tags=["neurology"]
        ))

        cardio_cards = asyncio.run(store.get_cards_by_topic("cardiology"))

        assert len(cardio_cards) == 1
        assert cardio_cards[0]["id"] == "card_topic_1"

    def test_update_card_status(self, store):
        """Changes validation status."""
        asyncio.run(store.insert_card(
            id="card_status",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="cloze",
            content="Status test",
            tags=[]
        ))

        asyncio.run(store.update_card_status("card_status", "valid"))

        cards = asyncio.run(store.get_cards_by_document("doc_cards"))
        card = next(c for c in cards if c["id"] == "card_status")
        assert card["status"] == "valid"

    def test_card_content_hash_unique(self, store):
        """No duplicate content allowed."""
        content = "Duplicate content {{c1::test}}"

        asyncio.run(store.insert_card(
            id="card_dup_1",
            document_id="doc_cards",
            chunk_id="chunk_cards",
            card_type="cloze",
            content=content,
            tags=[]
        ))

        with pytest.raises(Exception):
            asyncio.run(store.insert_card(
                id="card_dup_2",
                document_id="doc_cards",
                chunk_id="chunk_cards",
                card_type="cloze",
                content=content,
                tags=[]
            ))


class TestJobTracking:
    """Tests for job tracking operations."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test.db"
        s = SQLiteStore(db_path)
        asyncio.run(s.initialize())
        asyncio.run(s.insert_document(
            id="doc_jobs",
            source_path="/jobs.pdf",
            content_type="pdf_textbook",
            raw_text="Jobs test content",
            metadata={}
        ))
        yield s
        asyncio.run(s.close())

    def test_create_job(self, store):
        """Creates job with pending status."""
        job_id = asyncio.run(store.create_job(
            id="job_001",
            document_id="doc_jobs"
        ))

        assert job_id == "job_001"
        job = asyncio.run(store.get_job("job_001"))
        assert job["status"] == JobStatus.PENDING.value

    def test_update_job_status(self, store):
        """Pending -> processing -> completed."""
        asyncio.run(store.create_job(id="job_status", document_id="doc_jobs"))

        asyncio.run(store.update_job_status("job_status", JobStatus.PROCESSING))
        job = asyncio.run(store.get_job("job_status"))
        assert job["status"] == JobStatus.PROCESSING.value

        asyncio.run(store.update_job_status("job_status", JobStatus.COMPLETED))
        job = asyncio.run(store.get_job("job_status"))
        assert job["status"] == JobStatus.COMPLETED.value

    def test_job_progress(self, store):
        """Updates progress percentage."""
        asyncio.run(store.create_job(id="job_progress", document_id="doc_jobs"))

        asyncio.run(store.update_job_progress("job_progress", 50))
        job = asyncio.run(store.get_job("job_progress"))
        assert job["progress"] == 50

        asyncio.run(store.update_job_progress("job_progress", 100))
        job = asyncio.run(store.get_job("job_progress"))
        assert job["progress"] == 100

    def test_job_error(self, store):
        """Records error message."""
        asyncio.run(store.create_job(id="job_error", document_id="doc_jobs"))

        asyncio.run(store.set_job_error("job_error", "Processing failed: invalid format"))

        job = asyncio.run(store.get_job("job_error"))
        assert job["error"] == "Processing failed: invalid format"
        assert job["status"] == JobStatus.FAILED.value

    def test_get_job_by_id(self, store):
        """Retrieves job details."""
        asyncio.run(store.create_job(id="job_get", document_id="doc_jobs"))

        job = asyncio.run(store.get_job("job_get"))

        assert job is not None
        assert job["id"] == "job_get"
        assert job["document_id"] == "doc_jobs"
        assert "created_at" in job
        assert "updated_at" in job

    def test_list_recent_jobs(self, store):
        """Paginated job list."""
        for i in range(5):
            asyncio.run(store.create_job(id=f"job_list_{i}", document_id="doc_jobs"))

        jobs = asyncio.run(store.list_recent_jobs(limit=3))
        assert len(jobs) == 3

        jobs_all = asyncio.run(store.list_recent_jobs(limit=10))
        assert len(jobs_all) == 5


class TestAsyncOperations:
    """Tests for async database operations."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test.db"
        s = SQLiteStore(db_path)
        asyncio.run(s.initialize())
        yield s
        asyncio.run(s.close())

    def test_async_insert(self, store):
        """Async insert works."""
        async def run_insert():
            return await store.insert_document(
                id="doc_async",
                source_path="/async.pdf",
                content_type="pdf_textbook",
                raw_text="Async content",
                metadata={}
            )

        doc_id = asyncio.run(run_insert())
        assert doc_id == "doc_async"

    def test_async_query(self, store):
        """Async query works."""
        async def run_test():
            await store.insert_document(
                id="doc_query",
                source_path="/query.pdf",
                content_type="pdf_textbook",
                raw_text="Query content",
                metadata={}
            )
            return await store.get_document("doc_query")

        doc = asyncio.run(run_test())
        assert doc is not None
        assert doc["id"] == "doc_query"

    def test_connection_pool(self, store):
        """Reuses connections properly."""
        async def run_multiple_queries():
            tasks = []
            for i in range(10):
                tasks.append(store.insert_document(
                    id=f"doc_pool_{i}",
                    source_path=f"/pool_{i}.pdf",
                    content_type="pdf_textbook",
                    raw_text=f"Pool content {i}",
                    metadata={}
                ))
            await asyncio.gather(*tasks)
            return await store.list_documents()

        docs = asyncio.run(run_multiple_queries())
        assert len(docs) == 10
