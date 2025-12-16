"""Google OAuth authentication service."""

from __future__ import annotations

from typing import Any

from google.auth.transport import requests
from google.oauth2 import id_token


class GoogleAuthError(Exception):
    """Base exception for Google auth errors."""

    pass


class InvalidTokenError(GoogleAuthError):
    """Exception raised when token is invalid."""

    pass


class ExpiredTokenError(GoogleAuthError):
    """Exception raised when token is expired."""

    pass


class GoogleAuthService:
    """Service for verifying Google OAuth tokens."""

    def __init__(self, client_id: str):
        """Initialize the Google auth service.

        Args:
            client_id: The Google OAuth client ID

        Raises:
            ValueError: If client_id is empty
        """
        if not client_id:
            raise ValueError("Google client ID is required")
        self.client_id = client_id

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify a Google ID token.

        Args:
            token: The ID token from Google OAuth

        Returns:
            The decoded token payload

        Raises:
            InvalidTokenError: If the token is invalid
            ExpiredTokenError: If the token is expired
        """
        return self._verify_token(token)

    def _verify_token(self, token: str) -> dict[str, Any]:
        """Synchronous token verification.

        Args:
            token: The ID token from Google OAuth

        Returns:
            The decoded token payload

        Raises:
            InvalidTokenError: If the token is invalid
            ExpiredTokenError: If the token is expired
        """
        try:
            payload = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.client_id,
            )
            return payload
        except ValueError as e:
            error_msg = str(e).lower()
            if "expired" in error_msg:
                raise ExpiredTokenError("Token has expired") from e
            raise InvalidTokenError(f"Invalid token: {e}") from e

    def extract_user_info(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract user info from token payload.

        Args:
            payload: The decoded token payload

        Returns:
            Dictionary with user info (sub, email, name, picture)

        Raises:
            GoogleAuthError: If required fields are missing
        """
        required_fields = ["sub", "email", "name"]
        for field in required_fields:
            if field not in payload:
                raise GoogleAuthError(f"Missing required field: {field}")

        return {
            "sub": payload["sub"],
            "email": payload["email"],
            "name": payload["name"],
            "picture": payload.get("picture"),
        }

    def is_email_verified(self, payload: dict[str, Any]) -> bool:
        """Check if the user's email is verified.

        Args:
            payload: The decoded token payload

        Returns:
            True if email is verified, False otherwise
        """
        return payload.get("email_verified", False) is True
