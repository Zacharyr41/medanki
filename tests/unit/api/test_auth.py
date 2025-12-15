"""Tests for authentication API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from medanki_api.routes.auth import router, get_google_auth_service, get_jwt_service
from medanki.services.google_auth import GoogleAuthService, InvalidTokenError
from medanki.services.jwt_service import JWTService


@pytest.fixture
def mock_google_auth():
    """Mock Google auth service."""
    service = MagicMock(spec=GoogleAuthService)
    service.verify_token = AsyncMock(
        return_value={
            "sub": "google123",
            "email": "test@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "email_verified": True,
        }
    )
    service.extract_user_info.return_value = {
        "sub": "google123",
        "email": "test@gmail.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
    }
    service.is_email_verified.return_value = True
    return service


@pytest.fixture
def mock_jwt_service():
    """Mock JWT service."""
    service = MagicMock(spec=JWTService)
    service.create_access_token.return_value = "mock.jwt.token"
    service.decode_token.return_value = {"sub": "user123"}
    service.get_user_id_from_token.return_value = "user123"
    service.verify_token.return_value = True
    service.expiry_hours = 24
    return service


class MockUser:
    """Mock user object with actual string values."""

    def __init__(
        self,
        id: str = "user123",
        google_id: str = "google123",
        email: str = "test@gmail.com",
        name: str = "Test User",
        picture_url: str = "https://example.com/photo.jpg",
    ):
        self.id = id
        self.google_id = google_id
        self.email = email
        self.name = name
        self.picture_url = picture_url


@pytest.fixture
def app_with_mocks(mock_google_auth, mock_jwt_service):
    """Create test app with mocked services."""
    app = FastAPI()
    app.include_router(router, prefix="/api/auth")

    app.dependency_overrides[get_google_auth_service] = lambda: mock_google_auth
    app.dependency_overrides[get_jwt_service] = lambda: mock_jwt_service

    app.state.job_storage = {}
    app.state.user_repository = MagicMock()
    app.state.user_repository.get_or_create_user = AsyncMock(
        return_value=(MockUser(), True)
    )
    app.state.user_repository.get_user_by_id = AsyncMock(
        return_value=MockUser()
    )

    return app


@pytest.fixture
def client(app_with_mocks):
    """Create test client."""
    return TestClient(app_with_mocks)


class TestGoogleLogin:
    """Tests for POST /api/auth/google endpoint."""

    def test_google_login_creates_new_user(self, client, app_with_mocks):
        """Should create a new user on first login."""
        response = client.post(
            "/api/auth/google",
            json={"token": "valid_google_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "test@gmail.com"

    def test_google_login_existing_user_updates_login(self, client, app_with_mocks):
        """Should update last login for existing user."""
        app_with_mocks.state.user_repository.get_or_create_user = AsyncMock(
            return_value=(MockUser(), False)
        )

        response = client.post(
            "/api/auth/google",
            json={"token": "valid_google_token"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_google_login_returns_jwt(self, client, mock_jwt_service):
        """Should return a JWT token."""
        response = client.post(
            "/api/auth/google",
            json={"token": "valid_google_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock.jwt.token"
        mock_jwt_service.create_access_token.assert_called_once()

    def test_google_login_invalid_token(self, client, mock_google_auth):
        """Should return 401 for invalid Google token."""
        mock_google_auth.verify_token = AsyncMock(
            side_effect=InvalidTokenError("Invalid token")
        )

        response = client.post(
            "/api/auth/google",
            json={"token": "invalid_google_token"},
        )

        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_google_login_missing_token(self, client):
        """Should return 422 for missing token."""
        response = client.post("/api/auth/google", json={})

        assert response.status_code == 422


class TestGetCurrentUser:
    """Tests for GET /api/auth/me endpoint."""

    def test_get_current_user_valid_token(self, client, app_with_mocks):
        """Should return user info for valid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer mock.jwt.token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user123"
        assert data["email"] == "test@gmail.com"

    def test_get_current_user_invalid_token(self, client, mock_jwt_service):
        """Should return 401 for invalid token."""
        from medanki.services.jwt_service import InvalidTokenError

        mock_jwt_service.verify_token.return_value = False
        mock_jwt_service.get_user_id_from_token.side_effect = InvalidTokenError("Invalid")

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token"},
        )

        assert response.status_code == 401

    def test_get_current_user_missing_token(self, client):
        """Should return 401 for missing token."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_current_user_user_not_found(self, client, app_with_mocks):
        """Should return 404 if user not found in database."""
        app_with_mocks.state.user_repository.get_user_by_id = AsyncMock(
            return_value=None
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer mock.jwt.token"},
        )

        assert response.status_code == 404


class TestLogout:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(self, client):
        """Should return success message on logout."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer mock.jwt.token"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

    def test_logout_without_token(self, client):
        """Should still succeed even without token (idempotent)."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 200


class TestAuthResponseSchema:
    """Tests for authentication response structure."""

    def test_login_response_has_correct_structure(self, client):
        """Login response should have correct schema."""
        response = client.post(
            "/api/auth/google",
            json={"token": "valid_google_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data
        assert "id" in data["user"]
        assert "email" in data["user"]
        assert "name" in data["user"]
