"""Tests for download API routes."""

from __future__ import annotations

import sys

sys.path.insert(0, "/Users/zacharyrothstein/Code/medanki-tests/packages/api/src")
sys.path.insert(0, "/Users/zacharyrothstein/Code/medanki-tests/packages/core/src")

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from medanki_api.routes.download import router as download_router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(download_router, prefix="/api")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_store():
    store = AsyncMock()
    return store


@pytest.fixture
def sample_job():
    return {
        "id": "job_001",
        "document_id": "doc_001",
        "status": "completed",
        "progress": 100,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:05:00"
    }


@pytest.fixture
def sample_cards():
    return [
        {
            "id": "card_001",
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "card_type": "cloze",
            "content": json.dumps({
                "text": "The heart has {{c1::four}} chambers.",
                "extra": "Basic cardiac anatomy",
                "source": "Chapter 1"
            }),
            "tags": json.dumps(["cardiology", "anatomy", "1A"]),
            "status": "valid",
            "created_at": "2024-01-01T00:00:00"
        },
        {
            "id": "card_002",
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "card_type": "vignette",
            "content": json.dumps({
                "front": "A 45-year-old patient...",
                "answer": "Myocardial infarction",
                "explanation": "Classic presentation",
                "distinguishing_feature": "ST elevation"
            }),
            "tags": json.dumps(["cardiology", "emergency", "2B"]),
            "status": "valid",
            "created_at": "2024-01-01T00:00:00"
        },
        {
            "id": "card_003",
            "document_id": "doc_001",
            "chunk_id": "chunk_002",
            "card_type": "cloze",
            "content": json.dumps({
                "text": "The {{c1::left}} ventricle pumps to systemic circulation.",
                "extra": "",
                "source": "Chapter 1"
            }),
            "tags": json.dumps(["cardiology", "physiology", "1A"]),
            "status": "valid",
            "created_at": "2024-01-01T00:00:00"
        },
    ]


class TestDownload:
    """Tests for GET /api/jobs/{id}/download endpoint."""

    def test_download_apkg(self, client, mock_store, sample_job, sample_cards):
        """GET /api/jobs/{id}/download returns file."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            with patch("medanki_api.routes.download.generate_apkg") as mock_gen:
                mock_gen.return_value = b"APKG_CONTENT"
                response = client.get("/api/jobs/job_001/download")

        assert response.status_code == 200

    def test_download_not_ready(self, client, mock_store):
        """Job not complete returns 409."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "processing",
            "progress": 50
        }

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/download")

        assert response.status_code == 409

    def test_download_not_found(self, client, mock_store):
        """Unknown job returns 404."""
        mock_store.get_job.return_value = None

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            response = client.get("/api/jobs/unknown_job/download")

        assert response.status_code == 404

    def test_download_content_type(self, client, mock_store, sample_job, sample_cards):
        """Returns application/octet-stream."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            with patch("medanki_api.routes.download.generate_apkg") as mock_gen:
                mock_gen.return_value = b"APKG_CONTENT"
                response = client.get("/api/jobs/job_001/download")

        assert response.headers["content-type"] == "application/octet-stream"

    def test_download_filename(self, client, mock_store, sample_job, sample_cards):
        """Content-Disposition has filename."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            with patch("medanki_api.routes.download.generate_apkg") as mock_gen:
                mock_gen.return_value = b"APKG_CONTENT"
                response = client.get("/api/jobs/job_001/download")

        content_disposition = response.headers.get("content-disposition", "")
        assert "filename=" in content_disposition
        assert ".apkg" in content_disposition


class TestRegeneration:
    """Tests for POST /api/jobs/{id}/regenerate endpoint."""

    def test_regenerate_deck(self, client, mock_store, sample_job):
        """POST /api/jobs/{id}/regenerate creates new deck."""
        mock_store.get_job.return_value = sample_job

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            with patch("medanki_api.routes.download.create_processing_job") as mock_create:
                mock_create.return_value = "new_job_001"
                response = client.post("/api/jobs/job_001/regenerate")

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_regenerate_with_options(self, client, mock_store, sample_job):
        """Can change options."""
        mock_store.get_job.return_value = sample_job

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            with patch("medanki_api.routes.download.create_processing_job") as mock_create:
                mock_create.return_value = "new_job_002"
                response = client.post(
                    "/api/jobs/job_001/regenerate",
                    json={"deck_name": "Custom Deck", "include_tags": ["cardiology"]}
                )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_regenerate_creates_new_job(self, client, mock_store, sample_job):
        """Returns new job_id."""
        mock_store.get_job.return_value = sample_job

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            with patch("medanki_api.routes.download.create_processing_job") as mock_create:
                mock_create.return_value = "new_job_003"
                response = client.post("/api/jobs/job_001/regenerate")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "new_job_003"
        assert data["job_id"] != "job_001"


class TestStatistics:
    """Tests for GET /api/jobs/{id}/stats endpoint."""

    def test_job_stats(self, client, mock_store, sample_job, sample_cards):
        """GET /api/jobs/{id}/stats returns statistics."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        assert "counts" in data

    def test_stats_has_counts(self, client, mock_store, sample_job, sample_cards):
        """Card counts by type."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        counts = data["counts"]
        assert "total" in counts
        assert "cloze" in counts
        assert "vignette" in counts
        assert counts["total"] == 3
        assert counts["cloze"] == 2
        assert counts["vignette"] == 1

    def test_stats_has_topics(self, client, mock_store, sample_job, sample_cards):
        """Topic distribution."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        topics = data["topics"]
        assert "cardiology" in topics
        assert topics["cardiology"] == 3

    def test_stats_has_timing(self, client, mock_store, sample_job, sample_cards):
        """Processing duration."""
        mock_store.get_job.return_value = sample_job
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.download.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        assert "timing" in data
        assert "created_at" in data["timing"]
        assert "completed_at" in data["timing"]
        assert "duration_seconds" in data["timing"]
