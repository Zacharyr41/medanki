"""Tests for preview API endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from medanki_api.routes.preview import router


@pytest.fixture
def app_with_job():
    """Create test app with a completed job containing cards."""
    app = FastAPI()
    app.include_router(router, prefix="/api")

    app.state.job_storage = {
        "test-job-123": {
            "id": "test-job-123",
            "status": "completed",
            "progress": 100.0,
            "filename": "test.pdf",
            "exam": "MCAT",
            "cards_generated": 3,
            "cards": [
                {
                    "id": "card-1",
                    "type": "cloze",
                    "text": "The {{c1::mitochondria}} is the powerhouse of the cell.",
                    "topic_id": "MCAT",
                    "source_chunk": "Sample source text...",
                },
                {
                    "id": "card-2",
                    "type": "cloze",
                    "text": "{{c1::ATP}} is the primary energy currency.",
                    "topic_id": "MCAT",
                    "source_chunk": "Another source...",
                },
                {
                    "id": "card-3",
                    "type": "cloze",
                    "text": "The {{c1::Krebs cycle}} occurs in the mitochondrial matrix.",
                    "topic_id": "MCAT",
                    "source_chunk": "Third source...",
                },
            ],
        },
        "pending-job": {
            "id": "pending-job",
            "status": "processing",
            "progress": 50.0,
            "cards": [],
        },
    }

    return app


@pytest.fixture
def client(app_with_job):
    """Create test client."""
    return TestClient(app_with_job)


class TestPreviewEndpoint:
    """Tests for GET /api/jobs/{job_id}/preview."""

    def test_preview_returns_cards_for_completed_job(self, client):
        """Preview should return cards for a completed job."""
        response = client.get("/api/jobs/test-job-123/preview")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["cards"]) == 3
        assert data["cards"][0]["id"] == "card-1"
        assert "mitochondria" in data["cards"][0]["text"]

    def test_preview_returns_404_for_missing_job(self, client):
        """Preview should return 404 for non-existent job."""
        response = client.get("/api/jobs/nonexistent/preview")

        assert response.status_code == 404

    def test_preview_returns_409_for_incomplete_job(self, client):
        """Preview should return 409 for jobs not yet completed."""
        response = client.get("/api/jobs/pending-job/preview")

        assert response.status_code == 409

    def test_preview_pagination(self, client):
        """Preview should support pagination."""
        response = client.get("/api/jobs/test-job-123/preview?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["cards"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_preview_pagination_offset(self, client):
        """Preview should return correct cards with offset."""
        response = client.get("/api/jobs/test-job-123/preview?limit=2&offset=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["cards"]) == 1
        assert data["cards"][0]["id"] == "card-3"

    def test_preview_card_structure(self, client):
        """Preview cards should have correct structure."""
        response = client.get("/api/jobs/test-job-123/preview")

        assert response.status_code == 200
        card = response.json()["cards"][0]

        assert "id" in card
        assert "type" in card
        assert "text" in card
