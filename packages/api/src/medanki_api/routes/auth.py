"""Authentication API routes."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from medanki.services.google_auth import (
    ExpiredTokenError,
    GoogleAuthError,
    GoogleAuthService,
    InvalidTokenError,
)
from medanki.services.jwt_service import JWTError, JWTService

router = APIRouter()
security = HTTPBearer(auto_error=False)


class GoogleLoginRequest(BaseModel):
    """Request body for Google login."""

    token: str


class UserResponse(BaseModel):
    """User information in response."""

    id: str
    email: str
    name: str
    picture_url: str | None = None


class AuthResponse(BaseModel):
    """Response for successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserResponse


class LogoutResponse(BaseModel):
    """Response for logout."""

    message: str = "Successfully logged out"


def get_google_auth_service() -> GoogleAuthService:
    """Dependency for Google auth service."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )
    return GoogleAuthService(client_id=client_id)


def get_jwt_service() -> JWTService:
    """Dependency for JWT service."""
    secret_key = os.environ.get("JWT_SECRET_KEY", "")
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT not configured",
        )
    return JWTService(
        secret_key=secret_key,
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
        expiry_hours=int(os.environ.get("JWT_EXPIRY_HOURS", "24")),
    )


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> str:
    """Dependency to get the current user ID from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = jwt_service.get_user_id_from_token(credentials.credentials)
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/google", response_model=AuthResponse)
async def google_login(
    request: Request,
    body: GoogleLoginRequest,
    google_auth: Annotated[GoogleAuthService, Depends(get_google_auth_service)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> AuthResponse:
    """Authenticate with Google OAuth token.

    Exchange a Google ID token for a JWT access token.

    Args:
        request: The FastAPI request object
        body: The login request containing Google token
        google_auth: The Google auth service
        jwt_service: The JWT service

    Returns:
        AuthResponse with access token and user info

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        payload = await google_auth.verify_token(body.token)
    except (InvalidTokenError, ExpiredTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {e}",
        ) from e
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e}",
        ) from e

    user_info = google_auth.extract_user_info(payload)

    user_repo = request.app.state.user_repository
    user, created = await user_repo.get_or_create_user(user_info)

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        additional_claims={
            "email": user.email,
            "name": user.name,
        },
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_service.expiry_hours * 3600,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserResponse:
    """Get the current authenticated user.

    Args:
        request: The FastAPI request object
        user_id: The current user's ID from the JWT token

    Returns:
        UserResponse with user info

    Raises:
        HTTPException: 404 if user not found
    """
    user_repo = request.app.state.user_repository
    user = await user_repo.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout() -> LogoutResponse:
    """Log out the current user.

    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. This endpoint exists for API completeness.

    Returns:
        LogoutResponse with success message
    """
    return LogoutResponse()
