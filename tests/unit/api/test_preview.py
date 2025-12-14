"""Tests for preview API routes."""

from __future__ import annotations

import sys

sys.path.insert(0, "/Users/zacharyrothstein/Code/medanki-tests/packages/api/src")
sys.path.insert(0, "/Users/zacharyrothstein/Code/medanki-tests/packages/core/src")

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from medanki_api.routes.preview import router as preview_router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(preview_router, prefix="/api")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_store():
    store = AsyncMock()
    return store


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
                "front": "A 45-year-old patient presents with chest pain...",
                "answer": "Myocardial infarction",
                "explanation": "Classic presentation of MI",
                "distinguishing_feature": "ST elevation on ECG"
            }),
            "tags": json.dumps(["cardiology", "emergency", "2B"]),
            "status": "valid",
            "created_at": "2024-01-01T00:00:00"
        },
    ]


@pytest.fixture
def sample_chunk():
    return {
        "id": "chunk_001",
        "document_id": "doc_001",
        "text": "The heart has four chambers...",
        "start_char": 0,
        "end_char": 100,
        "token_count": 20,
        "section_path": json.dumps(["Cardiology", "Anatomy"])
    }


class TestCardPreview:
    """Tests for GET /api/jobs/{id}/preview endpoint."""

    def test_preview_job_cards(self, client, mock_store, sample_cards):
        """GET /api/jobs/{id}/preview returns cards."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 200
        data = response.json()
        assert "cards" in data
        assert len(data["cards"]) == 2

    def test_preview_not_ready(self, client, mock_store):
        """Job not complete returns 409."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "processing",
            "progress": 50
        }

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 409

    def test_preview_not_found(self, client, mock_store):
        """Unknown job returns 404."""
        mock_store.get_job.return_value = None

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/unknown_job/preview")

        assert response.status_code == 404

    def test_preview_paginated(self, client, mock_store, sample_cards):
        """Limit and offset work."""
        many_cards = sample_cards * 10
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = many_cards

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["cards"]) == 5
        assert data["total"] == 20
        assert data["limit"] == 5
        assert data["offset"] == 0

    def test_preview_has_card_data(self, client, mock_store, sample_cards):
        """Cards have text, type, tags."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 200
        data = response.json()
        card = data["cards"][0]
        assert "id" in card
        assert "type" in card
        assert "text" in card
        assert "tags" in card


class TestCardFormatPreview:
    """Tests for card format rendering in preview."""

    def test_cloze_preview_format(self, client, mock_store):
        """Cloze cards rendered properly."""
        cloze_card = {
            "id": "card_cloze",
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "card_type": "cloze",
            "content": json.dumps({
                "text": "The {{c1::mitral}} valve is between left atrium and ventricle.",
                "extra": "Cardiac valves",
                "source": "Chapter 2"
            }),
            "tags": json.dumps(["cardiology"]),
            "status": "valid",
            "created_at": "2024-01-01T00:00:00"
        }
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = [cloze_card]

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 200
        data = response.json()
        card = data["cards"][0]
        assert card["type"] == "cloze"
        assert "{{c1::" in card["text"]

    def test_vignette_preview_format(self, client, mock_store):
        """Vignettes have all fields."""
        vignette_card = {
            "id": "card_vignette",
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "card_type": "vignette",
            "content": json.dumps({
                "front": "A 55-year-old patient with crushing chest pain...",
                "answer": "Acute MI",
                "explanation": "Typical presentation",
                "distinguishing_feature": "Radiation to left arm"
            }),
            "tags": json.dumps(["cardiology"]),
            "status": "valid",
            "created_at": "2024-01-01T00:00:00"
        }
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = [vignette_card]

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 200
        data = response.json()
        card = data["cards"][0]
        assert card["type"] == "vignette"
        assert "front" in card
        assert "answer" in card
        assert "explanation" in card
        assert "distinguishing_feature" in card

    def test_preview_includes_topics(self, client, mock_store, sample_cards):
        """Topic matches included."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 200
        data = response.json()
        card = data["cards"][0]
        assert "topics" in card
        assert len(card["topics"]) > 0

    def test_preview_includes_source(self, client, mock_store, sample_cards, sample_chunk):
        """Source chunk reference included."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = sample_cards
        mock_store.get_chunks_by_document.return_value = [sample_chunk]

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview")

        assert response.status_code == 200
        data = response.json()
        card = data["cards"][0]
        assert "source" in card


class TestPreviewFiltering:
    """Tests for preview filtering options."""

    def test_filter_by_card_type(self, client, mock_store, sample_cards):
        """?type=cloze filters."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview?type=cloze")

        assert response.status_code == 200
        data = response.json()
        for card in data["cards"]:
            assert card["type"] == "cloze"

    def test_filter_by_topic(self, client, mock_store, sample_cards):
        """?topic=1A filters."""
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = sample_cards

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview?topic=1A")

        assert response.status_code == 200
        data = response.json()
        for card in data["cards"]:
            assert "1A" in card["topics"]

    def test_filter_by_status(self, client, mock_store, sample_cards):
        """?status=valid filters."""
        cards_with_invalid = sample_cards + [{
            "id": "card_invalid",
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "card_type": "cloze",
            "content": json.dumps({"text": "Invalid card"}),
            "tags": json.dumps([]),
            "status": "invalid",
            "created_at": "2024-01-01T00:00:00"
        }]
        mock_store.get_job.return_value = {
            "id": "job_001",
            "document_id": "doc_001",
            "status": "completed",
            "progress": 100
        }
        mock_store.get_cards_by_document.return_value = cards_with_invalid

        with patch("medanki_api.routes.preview.get_store", return_value=mock_store):
            response = client.get("/api/jobs/job_001/preview?status=valid")

        assert response.status_code == 200
        data = response.json()
        for card in data["cards"]:
            assert card["status"] == "valid"
