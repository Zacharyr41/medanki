"""Tests for JWT authentication service."""

from __future__ import annotations

import time
from datetime import timedelta

import pytest

from medanki.services.jwt_service import (
    InvalidTokenError,
    JWTError,
    JWTService,
    TokenExpiredError,
)


@pytest.fixture
def secret_key():
    """Sample secret key for testing."""
    return "test-secret-key-for-jwt-testing-12345"


@pytest.fixture
def jwt_service(secret_key: str):
    """Create a JWTService instance."""
    return JWTService(secret_key=secret_key, algorithm="HS256", expiry_hours=24)


@pytest.fixture
def short_expiry_service(secret_key: str):
    """Create a JWTService with very short expiry for testing expiration."""
    return JWTService(secret_key=secret_key, algorithm="HS256", expiry_hours=0)


class TestCreateAccessToken:
    """Tests for creating access tokens."""

    def test_create_access_token(self, jwt_service: JWTService):
        """Should create a valid JWT token."""
        token = jwt_service.create_access_token(user_id="user123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_user_id(self, jwt_service: JWTService):
        """Token should contain user_id in payload."""
        token = jwt_service.create_access_token(user_id="user123")
        payload = jwt_service.decode_token(token)

        assert payload["sub"] == "user123"

    def test_create_access_token_with_additional_claims(self, jwt_service: JWTService):
        """Should allow additional claims in token."""
        token = jwt_service.create_access_token(
            user_id="user123",
            additional_claims={"email": "test@example.com", "name": "Test User"},
        )
        payload = jwt_service.decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["name"] == "Test User"

    def test_create_access_token_has_expiry(self, jwt_service: JWTService):
        """Token should have expiry claim."""
        token = jwt_service.create_access_token(user_id="user123")
        payload = jwt_service.decode_token(token)

        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_create_access_token_has_issued_at(self, jwt_service: JWTService):
        """Token should have issued at claim."""
        token = jwt_service.create_access_token(user_id="user123")
        payload = jwt_service.decode_token(token)

        assert "iat" in payload
        assert payload["iat"] <= time.time()


class TestDecodeToken:
    """Tests for decoding tokens."""

    def test_decode_valid_token(self, jwt_service: JWTService):
        """Should decode a valid token."""
        token = jwt_service.create_access_token(user_id="user123")
        payload = jwt_service.decode_token(token)

        assert payload["sub"] == "user123"

    def test_decode_expired_token(self, short_expiry_service: JWTService):
        """Should raise TokenExpiredError for expired token."""
        token = short_expiry_service.create_access_token(
            user_id="user123",
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(TokenExpiredError):
            short_expiry_service.decode_token(token)

    def test_decode_invalid_token(self, jwt_service: JWTService):
        """Should raise InvalidTokenError for invalid token."""
        with pytest.raises(InvalidTokenError):
            jwt_service.decode_token("invalid.token.string")

    def test_decode_tampered_token(self, jwt_service: JWTService):
        """Should raise InvalidTokenError for tampered token."""
        token = jwt_service.create_access_token(user_id="user123")
        tampered = token[:-5] + "xxxxx"

        with pytest.raises(InvalidTokenError):
            jwt_service.decode_token(tampered)

    def test_decode_token_wrong_secret(self, jwt_service: JWTService):
        """Should raise InvalidTokenError when decoding with wrong secret."""
        token = jwt_service.create_access_token(user_id="user123")

        other_service = JWTService(
            secret_key="different-secret-key-12345",
            algorithm="HS256",
            expiry_hours=24,
        )

        with pytest.raises(InvalidTokenError):
            other_service.decode_token(token)


class TestJWTServiceInit:
    """Tests for service initialization."""

    def test_init_with_valid_params(self):
        """Should initialize with valid parameters."""
        service = JWTService(
            secret_key="test-secret-key-12345",
            algorithm="HS256",
            expiry_hours=24,
        )
        assert service.algorithm == "HS256"
        assert service.expiry_hours == 24

    def test_init_without_secret_key_raises_error(self):
        """Should raise error without secret key."""
        with pytest.raises(ValueError):
            JWTService(secret_key="", algorithm="HS256", expiry_hours=24)

    def test_init_with_default_algorithm(self):
        """Should use HS256 as default algorithm."""
        service = JWTService(secret_key="test-secret-key-12345")
        assert service.algorithm == "HS256"

    def test_init_with_default_expiry(self):
        """Should use 24 hours as default expiry."""
        service = JWTService(secret_key="test-secret-key-12345")
        assert service.expiry_hours == 24


class TestGetUserIdFromToken:
    """Tests for extracting user ID from token."""

    def test_get_user_id_from_token(self, jwt_service: JWTService):
        """Should extract user ID from valid token."""
        token = jwt_service.create_access_token(user_id="user123")
        user_id = jwt_service.get_user_id_from_token(token)

        assert user_id == "user123"

    def test_get_user_id_from_invalid_token(self, jwt_service: JWTService):
        """Should raise error for invalid token."""
        with pytest.raises(JWTError):
            jwt_service.get_user_id_from_token("invalid.token")


class TestVerifyToken:
    """Tests for token verification."""

    def test_verify_valid_token(self, jwt_service: JWTService):
        """Should return True for valid token."""
        token = jwt_service.create_access_token(user_id="user123")
        assert jwt_service.verify_token(token) is True

    def test_verify_invalid_token(self, jwt_service: JWTService):
        """Should return False for invalid token."""
        assert jwt_service.verify_token("invalid.token") is False

    def test_verify_expired_token(self, short_expiry_service: JWTService):
        """Should return False for expired token."""
        token = short_expiry_service.create_access_token(
            user_id="user123",
            expires_delta=timedelta(seconds=-1),
        )
        assert short_expiry_service.verify_token(token) is False
