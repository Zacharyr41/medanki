"""JWT authentication service for session management."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError as JoseJWTError
from jose import jwt


class JWTError(Exception):
    """Base exception for JWT errors."""

    pass


class InvalidTokenError(JWTError):
    """Exception raised when token is invalid."""

    pass


class TokenExpiredError(JWTError):
    """Exception raised when token is expired."""

    pass


class JWTService:
    """Service for creating and verifying JWT tokens."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expiry_hours: int = 24,
    ):
        """Initialize the JWT service.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            expiry_hours: Token expiry in hours (default: 24)

        Raises:
            ValueError: If secret_key is empty
        """
        if not secret_key:
            raise ValueError("JWT secret key is required")
        self._secret_key = secret_key
        self.algorithm = algorithm
        self.expiry_hours = expiry_hours

    def create_access_token(
        self,
        user_id: str,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a new access token.

        Args:
            user_id: The user ID to encode in the token
            additional_claims: Optional additional claims to include
            expires_delta: Optional custom expiry time

        Returns:
            The encoded JWT token
        """
        now = datetime.utcnow()

        if expires_delta is None:
            expires_delta = timedelta(hours=self.expiry_hours)

        expire = now + expires_delta

        payload: dict[str, Any] = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self._secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and verify a JWT token.

        Args:
            token: The JWT token to decode

        Returns:
            The decoded token payload

        Raises:
            TokenExpiredError: If the token has expired
            InvalidTokenError: If the token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except JoseJWTError as e:
            error_msg = str(e).lower()
            if "expired" in error_msg:
                raise TokenExpiredError("Token has expired") from e
            raise InvalidTokenError(f"Invalid token: {e}") from e

    def get_user_id_from_token(self, token: str) -> str:
        """Extract the user ID from a token.

        Args:
            token: The JWT token

        Returns:
            The user ID from the token

        Raises:
            JWTError: If the token is invalid or missing user ID
        """
        payload = self.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("Token missing user ID (sub claim)")
        return user_id

    def verify_token(self, token: str) -> bool:
        """Verify if a token is valid.

        Args:
            token: The JWT token to verify

        Returns:
            True if valid, False otherwise
        """
        try:
            self.decode_token(token)
            return True
        except JWTError:
            return False
