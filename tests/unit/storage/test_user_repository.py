"""Tests for UserRepository methods."""

from __future__ import annotations

from datetime import datetime

import pytest

from medanki.storage.sqlite import SQLiteStore
from medanki.storage.user_repository import User, UserRepository


@pytest.fixture
async def store(tmp_path):
    """Create a SQLite store for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def repo(store: SQLiteStore):
    """Create a UserRepository for testing."""
    return UserRepository(store)


@pytest.fixture
def sample_google_profile():
    """Sample Google OAuth profile data."""
    return {
        "sub": "google_123456789",
        "email": "testuser@gmail.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
    }


class TestUserModel:
    """Tests for the User model."""

    def test_user_model_fields(self):
        """User model should have all required fields."""
        user = User(
            id="user123",
            google_id="google_123",
            email="test@example.com",
            name="Test User",
            picture_url="https://example.com/pic.jpg",
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow(),
        )
        assert user.id == "user123"
        assert user.google_id == "google_123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.picture_url == "https://example.com/pic.jpg"


class TestCreateUser:
    """Tests for creating users."""

    async def test_create_user_from_google_profile(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Should create a user from Google profile data."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        assert user.google_id == sample_google_profile["sub"]
        assert user.email == sample_google_profile["email"]
        assert user.name == sample_google_profile["name"]
        assert user.picture_url == sample_google_profile["picture"]
        assert user.id is not None
        assert user.created_at is not None

    async def test_create_user_generates_unique_id(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Each created user should have a unique ID."""
        user1 = await repo.create_user_from_google_profile(sample_google_profile)

        profile2 = sample_google_profile.copy()
        profile2["sub"] = "google_different"
        profile2["email"] = "other@gmail.com"
        user2 = await repo.create_user_from_google_profile(profile2)

        assert user1.id != user2.id

    async def test_create_user_without_picture(self, repo: UserRepository):
        """Should handle Google profile without picture."""
        profile = {
            "sub": "google_no_pic",
            "email": "nopic@gmail.com",
            "name": "No Pic User",
        }
        user = await repo.create_user_from_google_profile(profile)

        assert user.picture_url is None


class TestGetUser:
    """Tests for retrieving users."""

    async def test_get_user_by_google_id(self, repo: UserRepository, sample_google_profile: dict):
        """Should retrieve user by Google ID."""
        created = await repo.create_user_from_google_profile(sample_google_profile)
        found = await repo.get_user_by_google_id(sample_google_profile["sub"])

        assert found is not None
        assert found.id == created.id
        assert found.google_id == created.google_id

    async def test_get_user_by_google_id_not_found(self, repo: UserRepository):
        """Should return None for non-existent Google ID."""
        found = await repo.get_user_by_google_id("nonexistent_google_id")
        assert found is None

    async def test_get_user_by_id(self, repo: UserRepository, sample_google_profile: dict):
        """Should retrieve user by internal ID."""
        created = await repo.create_user_from_google_profile(sample_google_profile)
        found = await repo.get_user_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    async def test_get_user_by_id_not_found(self, repo: UserRepository):
        """Should return None for non-existent user ID."""
        found = await repo.get_user_by_id("nonexistent_user_id")
        assert found is None


class TestUpdateUser:
    """Tests for updating users."""

    async def test_update_user_last_login(self, repo: UserRepository, sample_google_profile: dict):
        """Should update the last login timestamp."""
        user = await repo.create_user_from_google_profile(sample_google_profile)
        original_login = user.last_login

        import asyncio

        await asyncio.sleep(0.01)

        updated = await repo.update_last_login(user.id)

        assert updated is not None
        assert updated.last_login > original_login


class TestSavedCards:
    """Tests for saved cards functionality."""

    async def test_save_card_for_user(self, repo: UserRepository, sample_google_profile: dict):
        """Should save a card for a user."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        saved = await repo.save_card(
            user_id=user.id,
            job_id="job123",
            card_id="card456",
        )

        assert saved.user_id == user.id
        assert saved.job_id == "job123"
        assert saved.card_id == "card456"
        assert saved.saved_at is not None

    async def test_get_saved_cards_for_user(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Should retrieve all saved cards for a user."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        await repo.save_card(user_id=user.id, job_id="job1", card_id="card1")
        await repo.save_card(user_id=user.id, job_id="job1", card_id="card2")
        await repo.save_card(user_id=user.id, job_id="job2", card_id="card3")

        cards = await repo.get_saved_cards(user.id)

        assert len(cards) == 3
        card_ids = {c.card_id for c in cards}
        assert card_ids == {"card1", "card2", "card3"}

    async def test_get_saved_cards_with_pagination(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Should support pagination for saved cards."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        for i in range(5):
            await repo.save_card(user_id=user.id, job_id="job1", card_id=f"card{i}")

        page1 = await repo.get_saved_cards(user.id, limit=2, offset=0)
        page2 = await repo.get_saved_cards(user.id, limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

    async def test_remove_saved_card(self, repo: UserRepository, sample_google_profile: dict):
        """Should remove a saved card."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        await repo.save_card(user_id=user.id, job_id="job1", card_id="card1")
        await repo.save_card(user_id=user.id, job_id="job1", card_id="card2")

        await repo.remove_saved_card(user_id=user.id, card_id="card1")

        cards = await repo.get_saved_cards(user.id)
        assert len(cards) == 1
        assert cards[0].card_id == "card2"

    async def test_bulk_save_cards(self, repo: UserRepository, sample_google_profile: dict):
        """Should save multiple cards at once."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        card_ids = ["card1", "card2", "card3"]
        saved = await repo.bulk_save_cards(
            user_id=user.id,
            job_id="job123",
            card_ids=card_ids,
        )

        assert len(saved) == 3
        cards = await repo.get_saved_cards(user.id)
        assert len(cards) == 3

    async def test_cannot_save_duplicate_card(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Should not allow saving the same card twice."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        await repo.save_card(user_id=user.id, job_id="job1", card_id="card1")

        with pytest.raises(Exception):
            await repo.save_card(user_id=user.id, job_id="job1", card_id="card1")

    async def test_get_saved_cards_count(self, repo: UserRepository, sample_google_profile: dict):
        """Should return total count of saved cards."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        for i in range(5):
            await repo.save_card(user_id=user.id, job_id="job1", card_id=f"card{i}")

        count = await repo.get_saved_cards_count(user.id)
        assert count == 5

    async def test_saved_cards_empty_for_new_user(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """New user should have no saved cards."""
        user = await repo.create_user_from_google_profile(sample_google_profile)

        cards = await repo.get_saved_cards(user.id)
        assert cards == []

        count = await repo.get_saved_cards_count(user.id)
        assert count == 0


class TestGetOrCreateUser:
    """Tests for get_or_create_user functionality."""

    async def test_creates_new_user_if_not_exists(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Should create a new user if not exists."""
        user, created = await repo.get_or_create_user(sample_google_profile)

        assert created is True
        assert user.google_id == sample_google_profile["sub"]

    async def test_returns_existing_user_if_exists(
        self, repo: UserRepository, sample_google_profile: dict
    ):
        """Should return existing user without creating duplicate."""
        user1, created1 = await repo.get_or_create_user(sample_google_profile)
        user2, created2 = await repo.get_or_create_user(sample_google_profile)

        assert created1 is True
        assert created2 is False
        assert user1.id == user2.id
