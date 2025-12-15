"""Tests for download API routes."""

from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from medanki_api.routes.download import generate_apkg
from medanki_api.routes.download import router as download_router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(download_router, prefix="/api")
    app.state.job_storage = {}
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


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

    def test_download_apkg(self, client, sample_job, sample_cards):
        """GET /api/jobs/{id}/download returns file."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

        with patch("medanki_api.routes.download.generate_apkg") as mock_gen:
            mock_gen.return_value = b"APKG_CONTENT"
            response = client.get("/api/jobs/job_001/download")

        assert response.status_code == 200

    def test_download_not_ready(self, client):
        """Job not complete returns 409."""
        client.app.state.job_storage["job_001"] = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "processing",
            "progress": 50
        }

        response = client.get("/api/jobs/job_001/download")

        assert response.status_code == 409

    def test_download_not_found(self, client):
        """Unknown job returns 404."""
        response = client.get("/api/jobs/unknown_job/download")

        assert response.status_code == 404

    def test_download_content_type(self, client, sample_job, sample_cards):
        """Returns application/octet-stream."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

        with patch("medanki_api.routes.download.generate_apkg") as mock_gen:
            mock_gen.return_value = b"APKG_CONTENT"
            response = client.get("/api/jobs/job_001/download")

        assert response.headers["content-type"] == "application/octet-stream"

    def test_download_filename(self, client, sample_job, sample_cards):
        """Content-Disposition has filename."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

        with patch("medanki_api.routes.download.generate_apkg") as mock_gen:
            mock_gen.return_value = b"APKG_CONTENT"
            response = client.get("/api/jobs/job_001/download")

        content_disposition = response.headers.get("content-disposition", "")
        assert "filename=" in content_disposition
        assert ".apkg" in content_disposition


class TestRegeneration:
    """Tests for POST /api/jobs/{id}/regenerate endpoint."""

    def test_regenerate_deck(self, client, sample_job):
        """POST /api/jobs/{id}/regenerate creates new deck."""
        client.app.state.job_storage["job_001"] = sample_job

        with patch("medanki_api.routes.download.create_processing_job") as mock_create:
            mock_create.return_value = "new_job_001"
            response = client.post("/api/jobs/job_001/regenerate")

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_regenerate_with_options(self, client, sample_job):
        """Can change options."""
        client.app.state.job_storage["job_001"] = sample_job

        with patch("medanki_api.routes.download.create_processing_job") as mock_create:
            mock_create.return_value = "new_job_002"
            response = client.post(
                "/api/jobs/job_001/regenerate",
                json={"deck_name": "Custom Deck", "include_tags": ["cardiology"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_regenerate_creates_new_job(self, client, sample_job):
        """Returns new job_id."""
        client.app.state.job_storage["job_001"] = sample_job

        with patch("medanki_api.routes.download.create_processing_job") as mock_create:
            mock_create.return_value = "new_job_003"
            response = client.post("/api/jobs/job_001/regenerate")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "new_job_003"
        assert data["job_id"] != "job_001"


class TestStatistics:
    """Tests for GET /api/jobs/{id}/stats endpoint."""

    def test_job_stats(self, client, sample_job, sample_cards):
        """GET /api/jobs/{id}/stats returns statistics."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

        response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        assert "counts" in data

    def test_stats_has_counts(self, client, sample_job, sample_cards):
        """Card counts by type."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

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

    def test_stats_has_topics(self, client, sample_job, sample_cards):
        """Topic distribution."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

        response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        topics = data["topics"]
        assert "cardiology" in topics
        assert topics["cardiology"] == 3

    def test_stats_has_timing(self, client, sample_job, sample_cards):
        """Processing duration."""
        sample_job["cards"] = sample_cards
        client.app.state.job_storage["job_001"] = sample_job

        response = client.get("/api/jobs/job_001/stats")

        assert response.status_code == 200
        data = response.json()
        assert "timing" in data
        assert "created_at" in data["timing"]
        assert "completed_at" in data["timing"]
        assert "duration_seconds" in data["timing"]


class TestAPKGGeneration:
    """Tests for APKG file generation."""

    def test_generate_apkg_returns_valid_zip(self):
        """Generated APKG is a valid ZIP archive."""
        cards = [
            {
                "id": "card_001",
                "type": "cloze",
                "text": "The heart has {{c1::four}} chambers.",
                "topic_id": "cardiology",
                "source_chunk": "Chapter 1",
            }
        ]

        apkg_bytes = generate_apkg(cards, deck_name="Test Deck")

        assert zipfile.is_zipfile(io.BytesIO(apkg_bytes))

    def test_generate_apkg_contains_collection(self):
        """APKG contains collection.anki2 or collection.anki21 database."""
        cards = [
            {
                "id": "card_001",
                "type": "cloze",
                "text": "{{c1::DNA}} stores genetic information.",
                "topic_id": "genetics",
                "source_chunk": "Biology basics",
            }
        ]

        apkg_bytes = generate_apkg(cards, deck_name="Test Deck")

        with zipfile.ZipFile(io.BytesIO(apkg_bytes), "r") as zf:
            names = zf.namelist()
            has_collection = any("collection.anki2" in n for n in names)
            assert has_collection, f"Expected collection.anki2, got: {names}"

    def test_generate_apkg_with_multiple_cards(self):
        """APKG can contain multiple cards."""
        cards = [
            {
                "id": f"card_{i:03d}",
                "type": "cloze",
                "text": f"The {{{{c1::concept{i}}}}} is important.",
                "topic_id": "general",
                "source_chunk": f"Source {i}",
            }
            for i in range(5)
        ]

        apkg_bytes = generate_apkg(cards, deck_name="Multi Card Deck")

        assert zipfile.is_zipfile(io.BytesIO(apkg_bytes))

    def test_generate_apkg_with_vignette_cards(self):
        """APKG supports vignette card type."""
        cards = [
            {
                "id": "vig_001",
                "type": "vignette",
                "text": "A 45-year-old presents with chest pain...",
                "topic_id": "cardiology",
                "source_chunk": "Case study",
            }
        ]

        apkg_bytes = generate_apkg(cards, deck_name="Vignette Deck")

        assert zipfile.is_zipfile(io.BytesIO(apkg_bytes))

    def test_generate_apkg_empty_cards_returns_valid(self):
        """Empty card list still produces valid APKG."""
        apkg_bytes = generate_apkg([], deck_name="Empty Deck")

        assert zipfile.is_zipfile(io.BytesIO(apkg_bytes))

    def test_download_returns_real_apkg(self, client, sample_job):
        """Download endpoint returns actual APKG file, not stub."""
        sample_job["cards"] = [
            {
                "id": "card_001",
                "type": "cloze",
                "text": "The {{c1::mitochondria}} is the powerhouse.",
                "topic_id": "biology",
                "source_chunk": "Cell biology",
            }
        ]
        client.app.state.job_storage["job_001"] = sample_job

        response = client.get("/api/jobs/job_001/download")

        assert response.status_code == 200
        assert zipfile.is_zipfile(io.BytesIO(response.content))
