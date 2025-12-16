"""Integration tests for authentication API routes.

Tests the full auth flow including:
- Google OAuth token exchange (mocked)
- JWT token generation and validation
- User creation and retrieval
- Protected endpoint access
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    pass


@pytest.fixture
async def client(tmp_path):
    """Create async HTTP client with proper app lifecycle."""
    import os

    os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["JWT_EXPIRY_HOURS"] = "24"

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from medanki.storage.sqlite import SQLiteStore
    from medanki.storage.user_repository import UserRepository
    from medanki_api.routes import jobs_router, taxonomy_router, upload_router
    from medanki_api.routes.auth import router as auth_router
    from medanki_api.routes.download import router as download_router
    from medanki_api.routes.preview import router as preview_router
    from medanki_api.routes.saved_cards import router as saved_cards_router

    db_path = tmp_path / "test.db"

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(upload_router)
    app.include_router(jobs_router)
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(saved_cards_router, prefix="/api/saved-cards", tags=["saved_cards"])
    app.include_router(preview_router, prefix="/api", tags=["preview"])
    app.include_router(download_router, prefix="/api", tags=["download"])
    app.include_router(taxonomy_router, prefix="/api", tags=["taxonomy"])

    app.state.job_storage = {}
    sqlite_store = SQLiteStore(str(db_path))
    await sqlite_store.initialize()
    app.state.sqlite_store = sqlite_store
    app.state.user_repository = UserRepository(sqlite_store)

    app.state.job_storage["test-job"] = {
        "cards": [
            {"id": "card1", "text": "Test card 1"},
            {"id": "card2", "text": "Test card 2"},
        ]
    }
    app.state.job_storage["job-1"] = {
        "cards": [
            {"id": "card-a", "text": "Card A"},
            {"id": "card-b", "text": "Card B"},
        ]
    }
    app.state.job_storage["job-2"] = {
        "cards": [
            {"id": "card-c", "text": "Card C"},
        ]
    }
    app.state.job_storage["job-delete"] = {
        "cards": [
            {"id": "card-to-delete", "text": "Card to delete"},
        ]
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.state.job_storage.clear()
    await sqlite_store.close()


@pytest.fixture
def mock_google_token_info():
    """Mock Google token verification response."""
    return {
        "sub": "google-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "email_verified": True,
    }


class TestAuthRoutes:
    """Tests for /api/auth endpoints."""

    async def test_google_auth_missing_token(self, client: AsyncClient):
        """Test Google auth fails without token."""
        response = await client.post("/api/auth/google", json={})
        assert response.status_code == 422

    async def test_google_auth_invalid_token(self, client: AsyncClient):
        """Test Google auth fails with invalid token."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            response = await client.post("/api/auth/google", json={"token": "invalid-token"})
            assert response.status_code == 401
            assert "Invalid Google token" in response.json()["detail"]

    async def test_google_auth_success(self, client: AsyncClient, mock_google_token_info: dict):
        """Test successful Google auth creates user and returns JWT."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            response = await client.post("/api/auth/google", json={"token": "valid-google-token"})

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"
            assert data["user"]["name"] == "Test User"

    async def test_google_auth_returns_existing_user(
        self, client: AsyncClient, mock_google_token_info: dict
    ):
        """Test Google auth returns existing user on repeat login."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            response1 = await client.post("/api/auth/google", json={"token": "valid-google-token"})
            user_id_1 = response1.json()["user"]["id"]

            response2 = await client.post("/api/auth/google", json={"token": "valid-google-token"})
            user_id_2 = response2.json()["user"]["id"]

            assert user_id_1 == user_id_2

    async def test_get_current_user_without_token(self, client: AsyncClient):
        """Test /me endpoint fails without auth token."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_get_current_user_with_invalid_token(self, client: AsyncClient):
        """Test /me endpoint fails with invalid token."""
        response = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    async def test_get_current_user_with_valid_token(
        self, client: AsyncClient, mock_google_token_info: dict
    ):
        """Test /me endpoint returns user with valid token."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            access_token = auth_response.json()["access_token"]

            response = await client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
            )

            assert response.status_code == 200
            user = response.json()
            assert user["email"] == "test@example.com"
            assert user["name"] == "Test User"


class TestSavedCardsRoutes:
    """Tests for /api/saved-cards endpoints."""

    async def test_save_cards_without_auth(self, client: AsyncClient):
        """Test saving cards fails without authentication."""
        response = await client.post(
            "/api/saved-cards",
            json={"job_id": "test-job", "card_ids": ["card1", "card2"]},
        )
        assert response.status_code == 401

    async def test_save_cards_with_auth(self, client: AsyncClient, mock_google_token_info: dict):
        """Test saving cards succeeds with authentication."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            access_token = auth_response.json()["access_token"]

            response = await client.post(
                "/api/saved-cards",
                json={"job_id": "test-job", "card_ids": ["card1", "card2"]},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["saved_count"] == 2

    async def test_get_saved_cards_without_auth(self, client: AsyncClient):
        """Test getting saved cards fails without authentication."""
        response = await client.get("/api/saved-cards")
        assert response.status_code == 401

    async def test_get_saved_cards_with_auth(
        self, client: AsyncClient, mock_google_token_info: dict
    ):
        """Test getting saved cards returns empty list for new user."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            access_token = auth_response.json()["access_token"]

            response = await client.get(
                "/api/saved-cards",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "cards" in data
            assert isinstance(data["cards"], list)

    async def test_save_and_retrieve_cards(self, client: AsyncClient, mock_google_token_info: dict):
        """Test full flow of saving and retrieving cards."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            access_token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            await client.post(
                "/api/saved-cards",
                json={"job_id": "job-1", "card_ids": ["card-a", "card-b"]},
                headers=headers,
            )

            await client.post(
                "/api/saved-cards",
                json={"job_id": "job-2", "card_ids": ["card-c"]},
                headers=headers,
            )

            response = await client.get("/api/saved-cards", headers=headers)
            data = response.json()

            assert len(data["cards"]) == 3
            card_ids = [c["card_id"] for c in data["cards"]]
            assert "card-a" in card_ids
            assert "card-b" in card_ids
            assert "card-c" in card_ids

    async def test_delete_saved_card(self, client: AsyncClient, mock_google_token_info: dict):
        """Test deleting a saved card."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            access_token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            await client.post(
                "/api/saved-cards",
                json={"job_id": "job-delete", "card_ids": ["card-to-delete"]},
                headers=headers,
            )

            response = await client.delete("/api/saved-cards/card-to-delete", headers=headers)
            assert response.status_code == 200

            get_response = await client.get("/api/saved-cards", headers=headers)
            cards = get_response.json()["cards"]
            card_ids = [c["card_id"] for c in cards]
            assert "card-to-delete" not in card_ids

    async def test_saved_cards_persist_after_logout_and_login(
        self, client: AsyncClient, mock_google_token_info: dict
    ):
        """Test that saved cards persist after user logs out and logs back in."""
        with patch("medanki.services.google_auth.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_token_info

            auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            access_token = auth_response.json()["access_token"]
            user_id = auth_response.json()["user"]["id"]
            headers = {"Authorization": f"Bearer {access_token}"}

            save_response = await client.post(
                "/api/saved-cards",
                json={"job_id": "job-1", "card_ids": ["card-a", "card-b"]},
                headers=headers,
            )
            assert save_response.status_code == 200

            get_response = await client.get("/api/saved-cards", headers=headers)
            assert len(get_response.json()["cards"]) == 2

            new_auth_response = await client.post(
                "/api/auth/google", json={"token": "valid-google-token"}
            )
            new_access_token = new_auth_response.json()["access_token"]
            new_user_id = new_auth_response.json()["user"]["id"]
            new_headers = {"Authorization": f"Bearer {new_access_token}"}

            assert new_user_id == user_id

            get_after_relogin = await client.get("/api/saved-cards", headers=new_headers)
            data = get_after_relogin.json()

            assert len(data["cards"]) == 2
            card_ids = [c["card_id"] for c in data["cards"]]
            assert "card-a" in card_ids
            assert "card-b" in card_ids
