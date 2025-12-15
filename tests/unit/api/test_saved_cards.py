"""Tests for saved cards API routes."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from medanki.services.jwt_service import JWTService
from medanki_api.routes.auth import get_current_user_id, get_jwt_service
from medanki_api.routes.saved_cards import router


class MockUser:
    """Mock user object."""

    def __init__(self, id: str = "user123"):
        self.id = id
        self.google_id = "google123"
        self.email = "test@gmail.com"
        self.name = "Test User"
        self.picture_url = "https://example.com/photo.jpg"


class MockSavedCard:
    """Mock saved card object."""

    def __init__(
        self,
        id: str = "sc1",
        user_id: str = "user123",
        job_id: str = "job123",
        card_id: str = "card456",
    ):
        self.id = id
        self.user_id = user_id
        self.job_id = job_id
        self.card_id = card_id
        self.saved_at = datetime.utcnow()


@pytest.fixture
def mock_jwt_service():
    """Mock JWT service."""
    service = MagicMock(spec=JWTService)
    service.get_user_id_from_token.return_value = "user123"
    service.verify_token.return_value = True
    service.expiry_hours = 24
    return service


@pytest.fixture
def mock_user_repository():
    """Mock user repository."""
    repo = MagicMock()
    repo.save_card = AsyncMock(return_value=MockSavedCard())
    repo.bulk_save_cards = AsyncMock(
        return_value=[
            MockSavedCard(id="sc1", card_id="card1"),
            MockSavedCard(id="sc2", card_id="card2"),
        ]
    )
    repo.get_saved_cards = AsyncMock(
        return_value=[
            MockSavedCard(id="sc1", card_id="card1"),
            MockSavedCard(id="sc2", card_id="card2"),
        ]
    )
    repo.get_saved_cards_count = AsyncMock(return_value=2)
    repo.remove_saved_card = AsyncMock()
    repo.get_user_by_id = AsyncMock(return_value=MockUser())
    return repo


@pytest.fixture
def app_with_mocks(mock_jwt_service, mock_user_repository):
    """Create test app with mocked services."""
    app = FastAPI()
    app.include_router(router, prefix="/api/saved-cards")

    app.dependency_overrides[get_jwt_service] = lambda: mock_jwt_service
    app.dependency_overrides[get_current_user_id] = lambda: "user123"

    app.state.user_repository = mock_user_repository
    app.state.job_storage = {
        "job123": {
            "id": "job123",
            "status": "completed",
            "cards": [
                {"id": "card1", "type": "cloze", "text": "Test card 1"},
                {"id": "card2", "type": "cloze", "text": "Test card 2"},
                {"id": "card3", "type": "cloze", "text": "Test card 3"},
            ],
        }
    }

    return app


@pytest.fixture
def client(app_with_mocks):
    """Create test client."""
    return TestClient(app_with_mocks)


@pytest.fixture
def auth_headers():
    """Authorization headers."""
    return {"Authorization": "Bearer mock.jwt.token"}


class TestSaveCards:
    """Tests for POST /api/saved-cards endpoint."""

    def test_save_cards_requires_auth(self, app_with_mocks):
        """Should require authentication."""
        app_with_mocks.dependency_overrides.pop(get_current_user_id)
        client = TestClient(app_with_mocks)

        response = client.post(
            "/api/saved-cards",
            json={"job_id": "job123", "card_ids": ["card1"]},
        )

        assert response.status_code == 401

    def test_save_single_card(self, client, auth_headers, mock_user_repository):
        """Should save a single card."""
        response = client.post(
            "/api/saved-cards",
            json={"job_id": "job123", "card_ids": ["card1"]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["saved_count"] == 1
        mock_user_repository.save_card.assert_called()

    def test_save_multiple_cards(self, client, auth_headers, mock_user_repository):
        """Should save multiple cards."""
        mock_user_repository.save_card = AsyncMock(
            side_effect=[
                MockSavedCard(id="sc1", card_id="card1"),
                MockSavedCard(id="sc2", card_id="card2"),
            ]
        )

        response = client.post(
            "/api/saved-cards",
            json={"job_id": "job123", "card_ids": ["card1", "card2"]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["saved_count"] == 2

    def test_save_cards_invalid_job(self, client, auth_headers):
        """Should return 404 for non-existent job."""
        response = client.post(
            "/api/saved-cards",
            json={"job_id": "nonexistent", "card_ids": ["card1"]},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_save_cards_empty_list(self, client, auth_headers):
        """Should return 422 (validation error) for empty card list."""
        response = client.post(
            "/api/saved-cards",
            json={"job_id": "job123", "card_ids": []},
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestGetSavedCards:
    """Tests for GET /api/saved-cards endpoint."""

    def test_get_saved_cards_paginated(self, client, auth_headers, mock_user_repository):
        """Should return paginated saved cards."""
        response = client.get(
            "/api/saved-cards?limit=10&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "cards" in data
        assert "total" in data
        assert data["total"] == 2
        mock_user_repository.get_saved_cards.assert_called_once()

    def test_get_saved_cards_default_pagination(self, client, auth_headers):
        """Should use default pagination."""
        response = client.get("/api/saved-cards", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "offset" in data


class TestRemoveSavedCard:
    """Tests for DELETE /api/saved-cards/{card_id} endpoint."""

    def test_remove_saved_card(self, client, auth_headers, mock_user_repository):
        """Should remove a saved card."""
        response = client.delete(
            "/api/saved-cards/card1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        mock_user_repository.remove_saved_card.assert_called_once_with(
            user_id="user123", card_id="card1"
        )

    def test_remove_saved_card_requires_auth(self, app_with_mocks):
        """Should require authentication."""
        app_with_mocks.dependency_overrides.pop(get_current_user_id)
        client = TestClient(app_with_mocks)

        response = client.delete("/api/saved-cards/card1")

        assert response.status_code == 401


class TestExportSavedCards:
    """Tests for GET /api/saved-cards/export endpoint."""

    def test_export_saved_cards(self, client, auth_headers, app_with_mocks):
        """Should export saved cards as apkg."""
        response = client.get(
            "/api/saved-cards/export",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_export_empty_saved_cards(self, client, auth_headers, mock_user_repository):
        """Should return 400 when no cards to export."""
        mock_user_repository.get_saved_cards = AsyncMock(return_value=[])
        mock_user_repository.get_saved_cards_count = AsyncMock(return_value=0)

        response = client.get(
            "/api/saved-cards/export",
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestSavedCardsResponseSchema:
    """Tests for response schemas."""

    def test_saved_card_response_structure(self, client, auth_headers):
        """Saved card response should have correct structure."""
        response = client.get("/api/saved-cards", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "cards" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        if data["cards"]:
            card = data["cards"][0]
            assert "id" in card
            assert "card_id" in card
            assert "job_id" in card
            assert "saved_at" in card
