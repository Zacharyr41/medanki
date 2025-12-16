"""Tests for Google OAuth authentication service."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from medanki.services.google_auth import (
    ExpiredTokenError,
    GoogleAuthError,
    GoogleAuthService,
    InvalidTokenError,
)


@pytest.fixture
def google_client_id():
    """Sample Google client ID."""
    return "test-client-id.apps.googleusercontent.com"


@pytest.fixture
def auth_service(google_client_id: str):
    """Create a GoogleAuthService instance."""
    return GoogleAuthService(client_id=google_client_id)


@pytest.fixture
def valid_google_payload():
    """Sample valid Google token payload."""
    return {
        "iss": "https://accounts.google.com",
        "azp": "test-client-id.apps.googleusercontent.com",
        "aud": "test-client-id.apps.googleusercontent.com",
        "sub": "123456789012345678901",
        "email": "testuser@gmail.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "https://lh3.googleusercontent.com/a/photo",
        "given_name": "Test",
        "family_name": "User",
        "iat": 1700000000,
        "exp": 1700003600,
    }


class TestVerifyGoogleToken:
    """Tests for token verification."""

    async def test_verify_google_token_valid(
        self, auth_service: GoogleAuthService, valid_google_payload: dict
    ):
        """Should return payload for valid token."""
        with patch.object(auth_service, "_verify_token", return_value=valid_google_payload):
            result = await auth_service.verify_token("valid_token")

        assert result == valid_google_payload
        assert result["sub"] == "123456789012345678901"
        assert result["email"] == "testuser@gmail.com"

    async def test_verify_google_token_invalid(self, auth_service: GoogleAuthService):
        """Should raise InvalidTokenError for invalid token."""
        with patch.object(
            auth_service,
            "_verify_token",
            side_effect=InvalidTokenError("Invalid token"),
        ):
            with pytest.raises(InvalidTokenError):
                await auth_service.verify_token("invalid_token")

    async def test_verify_google_token_expired(self, auth_service: GoogleAuthService):
        """Should raise ExpiredTokenError for expired token."""
        with patch.object(
            auth_service,
            "_verify_token",
            side_effect=ExpiredTokenError("Token expired"),
        ):
            with pytest.raises(ExpiredTokenError):
                await auth_service.verify_token("expired_token")

    async def test_verify_token_wrong_audience(self, valid_google_payload: dict):
        """Should reject token with wrong audience."""
        service = GoogleAuthService(client_id="different-client-id")
        payload = valid_google_payload.copy()
        payload["aud"] = "wrong-client-id"

        with patch.object(
            service,
            "_verify_token",
            side_effect=InvalidTokenError("Wrong audience"),
        ):
            with pytest.raises(InvalidTokenError):
                await service.verify_token("token_with_wrong_aud")


class TestExtractUserInfo:
    """Tests for extracting user info from token payload."""

    def test_extract_user_info_from_token(
        self, auth_service: GoogleAuthService, valid_google_payload: dict
    ):
        """Should extract user profile from payload."""
        user_info = auth_service.extract_user_info(valid_google_payload)

        assert user_info["sub"] == "123456789012345678901"
        assert user_info["email"] == "testuser@gmail.com"
        assert user_info["name"] == "Test User"
        assert user_info["picture"] == "https://lh3.googleusercontent.com/a/photo"

    def test_extract_user_info_without_picture(
        self, auth_service: GoogleAuthService, valid_google_payload: dict
    ):
        """Should handle missing picture in payload."""
        payload = valid_google_payload.copy()
        del payload["picture"]

        user_info = auth_service.extract_user_info(payload)

        assert user_info["sub"] == "123456789012345678901"
        assert user_info.get("picture") is None

    def test_extract_user_info_missing_required_field(
        self, auth_service: GoogleAuthService, valid_google_payload: dict
    ):
        """Should raise error for missing required field."""
        payload = valid_google_payload.copy()
        del payload["email"]

        with pytest.raises(GoogleAuthError):
            auth_service.extract_user_info(payload)


class TestGoogleAuthServiceInit:
    """Tests for service initialization."""

    def test_init_with_client_id(self):
        """Should initialize with client ID."""
        service = GoogleAuthService(client_id="test-client-id")
        assert service.client_id == "test-client-id"

    def test_init_without_client_id_raises_error(self):
        """Should raise error without client ID."""
        with pytest.raises(ValueError):
            GoogleAuthService(client_id="")


class TestVerifyEmailVerified:
    """Tests for email verification check."""

    def test_email_verified_true(self, auth_service: GoogleAuthService, valid_google_payload: dict):
        """Should pass when email is verified."""
        assert auth_service.is_email_verified(valid_google_payload) is True

    def test_email_verified_false(
        self, auth_service: GoogleAuthService, valid_google_payload: dict
    ):
        """Should return False when email is not verified."""
        payload = valid_google_payload.copy()
        payload["email_verified"] = False

        assert auth_service.is_email_verified(payload) is False

    def test_email_verified_missing(
        self, auth_service: GoogleAuthService, valid_google_payload: dict
    ):
        """Should return False when email_verified is missing."""
        payload = valid_google_payload.copy()
        del payload["email_verified"]

        assert auth_service.is_email_verified(payload) is False
