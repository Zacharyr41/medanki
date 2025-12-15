"""User repository for authentication and saved cards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from medanki.storage.sqlite import SQLiteStore


@dataclass
class User:
    """Represents a user in the system."""

    id: str
    google_id: str
    email: str
    name: str
    picture_url: str | None
    created_at: datetime
    last_login: datetime


@dataclass
class SavedCard:
    """Represents a card saved by a user."""

    id: str
    user_id: str
    job_id: str
    card_id: str
    saved_at: datetime


class UserRepository:
    """Repository for user and saved card operations."""

    def __init__(self, store: SQLiteStore):
        self._store = store

    async def create_user_from_google_profile(self, profile: dict) -> User:
        """Create a new user from Google OAuth profile.

        Args:
            profile: Google OAuth profile containing sub, email, name, picture

        Returns:
            The created User instance
        """
        conn = await self._store._get_connection()
        user_id = str(uuid4())
        now = datetime.utcnow()

        await conn.execute(
            """
            INSERT INTO users (id, google_id, email, name, picture_url, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                profile["sub"],
                profile["email"],
                profile["name"],
                profile.get("picture"),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await conn.commit()

        return User(
            id=user_id,
            google_id=profile["sub"],
            email=profile["email"],
            name=profile["name"],
            picture_url=profile.get("picture"),
            created_at=now,
            last_login=now,
        )

    async def get_user_by_google_id(self, google_id: str) -> User | None:
        """Get a user by their Google ID.

        Args:
            google_id: The Google OAuth subject ID

        Returns:
            User if found, None otherwise
        """
        conn = await self._store._get_connection()
        cursor = await conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
        row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get a user by their internal ID.

        Args:
            user_id: The internal user ID

        Returns:
            User if found, None otherwise
        """
        conn = await self._store._get_connection()
        cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    async def update_last_login(self, user_id: str) -> User | None:
        """Update the last login timestamp for a user.

        Args:
            user_id: The user ID to update

        Returns:
            Updated User if found, None otherwise
        """
        conn = await self._store._get_connection()
        now = datetime.utcnow()

        await conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (now.isoformat(), user_id),
        )
        await conn.commit()

        return await self.get_user_by_id(user_id)

    async def get_or_create_user(self, profile: dict) -> tuple[User, bool]:
        """Get an existing user or create a new one.

        Args:
            profile: Google OAuth profile

        Returns:
            Tuple of (User, created) where created is True if user was created
        """
        existing = await self.get_user_by_google_id(profile["sub"])
        if existing:
            await self.update_last_login(existing.id)
            return existing, False

        user = await self.create_user_from_google_profile(profile)
        return user, True

    async def save_card(self, user_id: str, job_id: str, card_id: str) -> SavedCard:
        """Save a card for a user.

        Args:
            user_id: The user ID
            job_id: The job ID the card belongs to
            card_id: The card ID to save

        Returns:
            The created SavedCard instance

        Raises:
            Exception: If card is already saved
        """
        conn = await self._store._get_connection()
        saved_id = str(uuid4())
        now = datetime.utcnow()

        await conn.execute(
            """
            INSERT INTO saved_cards (id, user_id, job_id, card_id, saved_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (saved_id, user_id, job_id, card_id, now.isoformat()),
        )
        await conn.commit()

        return SavedCard(
            id=saved_id,
            user_id=user_id,
            job_id=job_id,
            card_id=card_id,
            saved_at=now,
        )

    async def bulk_save_cards(
        self, user_id: str, job_id: str, card_ids: list[str]
    ) -> list[SavedCard]:
        """Save multiple cards at once.

        Args:
            user_id: The user ID
            job_id: The job ID the cards belong to
            card_ids: List of card IDs to save

        Returns:
            List of created SavedCard instances
        """
        saved = []
        for card_id in card_ids:
            sc = await self.save_card(user_id, job_id, card_id)
            saved.append(sc)
        return saved

    async def get_saved_cards(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[SavedCard]:
        """Get saved cards for a user.

        Args:
            user_id: The user ID
            limit: Maximum number of cards to return
            offset: Number of cards to skip

        Returns:
            List of SavedCard instances
        """
        conn = await self._store._get_connection()
        cursor = await conn.execute(
            """
            SELECT * FROM saved_cards
            WHERE user_id = ?
            ORDER BY saved_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )
        rows = await cursor.fetchall()

        return [self._row_to_saved_card(row) for row in rows]

    async def get_saved_cards_count(self, user_id: str) -> int:
        """Get the total count of saved cards for a user.

        Args:
            user_id: The user ID

        Returns:
            Total count of saved cards
        """
        conn = await self._store._get_connection()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM saved_cards WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row[0]

    async def remove_saved_card(self, user_id: str, card_id: str) -> None:
        """Remove a saved card.

        Args:
            user_id: The user ID
            card_id: The card ID to remove
        """
        conn = await self._store._get_connection()
        await conn.execute(
            "DELETE FROM saved_cards WHERE user_id = ? AND card_id = ?",
            (user_id, card_id),
        )
        await conn.commit()

    def _row_to_user(self, row) -> User:
        """Convert a database row to a User instance."""
        return User(
            id=row["id"],
            google_id=row["google_id"],
            email=row["email"],
            name=row["name"],
            picture_url=row["picture_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_login=datetime.fromisoformat(row["last_login"]),
        )

    def _row_to_saved_card(self, row) -> SavedCard:
        """Convert a database row to a SavedCard instance."""
        return SavedCard(
            id=row["id"],
            user_id=row["user_id"],
            job_id=row["job_id"],
            card_id=row["card_id"],
            saved_at=datetime.fromisoformat(row["saved_at"]),
        )
