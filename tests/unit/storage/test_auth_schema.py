"""Tests for authentication database schema."""

from __future__ import annotations

import pytest

from medanki.storage.sqlite import SQLiteStore


@pytest.fixture
async def store(tmp_path):
    """Create a SQLite store for testing."""
    db_path = tmp_path / "test.db"
    store = SQLiteStore(db_path)
    await store.initialize()
    yield store
    await store.close()


class TestUsersTable:
    """Tests for the users table schema."""

    async def test_users_table_exists(self, store: SQLiteStore):
        """Users table should be created during initialization."""
        tables = await store._get_tables()
        assert "users" in tables

    async def test_users_table_has_required_columns(self, store: SQLiteStore):
        """Users table should have all required columns."""
        columns = await store._get_table_columns("users")
        expected_columns = {
            "id",
            "google_id",
            "email",
            "name",
            "picture_url",
            "created_at",
            "last_login",
        }
        assert set(columns) >= expected_columns

    async def test_users_google_id_unique_constraint(self, store: SQLiteStore):
        """Google ID should have a unique constraint."""
        conn = await store._get_connection()

        await conn.execute(
            """
            INSERT INTO users (id, google_id, email, name, created_at, last_login)
            VALUES ('user1', 'google123', 'test@example.com', 'Test User', datetime('now'), datetime('now'))
            """
        )
        await conn.commit()

        with pytest.raises(Exception):
            await conn.execute(
                """
                INSERT INTO users (id, google_id, email, name, created_at, last_login)
                VALUES ('user2', 'google123', 'other@example.com', 'Other User', datetime('now'), datetime('now'))
                """
            )
            await conn.commit()


class TestSavedCardsTable:
    """Tests for the saved_cards table schema."""

    async def test_saved_cards_table_exists(self, store: SQLiteStore):
        """Saved cards table should be created during initialization."""
        tables = await store._get_tables()
        assert "saved_cards" in tables

    async def test_saved_cards_table_has_required_columns(self, store: SQLiteStore):
        """Saved cards table should have all required columns."""
        columns = await store._get_table_columns("saved_cards")
        expected_columns = {"id", "user_id", "job_id", "card_id", "saved_at"}
        assert set(columns) >= expected_columns

    async def test_saved_cards_has_user_foreign_key(self, store: SQLiteStore):
        """Saved cards should have a foreign key to users table."""
        conn = await store._get_connection()

        await conn.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(Exception):
            await conn.execute(
                """
                INSERT INTO saved_cards (id, user_id, job_id, card_id, saved_at)
                VALUES ('sc1', 'nonexistent_user', 'job123', 'card456', datetime('now'))
                """
            )
            await conn.commit()

    async def test_unique_constraint_on_user_card_pair(self, store: SQLiteStore):
        """User cannot save the same card twice."""
        conn = await store._get_connection()

        await conn.execute(
            """
            INSERT INTO users (id, google_id, email, name, created_at, last_login)
            VALUES ('user1', 'google123', 'test@example.com', 'Test User', datetime('now'), datetime('now'))
            """
        )
        await conn.commit()

        await conn.execute(
            """
            INSERT INTO saved_cards (id, user_id, job_id, card_id, saved_at)
            VALUES ('sc1', 'user1', 'job123', 'card456', datetime('now'))
            """
        )
        await conn.commit()

        with pytest.raises(Exception):
            await conn.execute(
                """
                INSERT INTO saved_cards (id, user_id, job_id, card_id, saved_at)
                VALUES ('sc2', 'user1', 'job123', 'card456', datetime('now'))
                """
            )
            await conn.commit()

    async def test_saved_cards_cascade_delete_on_user_delete(self, store: SQLiteStore):
        """Saved cards should be deleted when user is deleted."""
        conn = await store._get_connection()

        await conn.execute(
            """
            INSERT INTO users (id, google_id, email, name, created_at, last_login)
            VALUES ('user1', 'google123', 'test@example.com', 'Test User', datetime('now'), datetime('now'))
            """
        )
        await conn.execute(
            """
            INSERT INTO saved_cards (id, user_id, job_id, card_id, saved_at)
            VALUES ('sc1', 'user1', 'job123', 'card456', datetime('now'))
            """
        )
        await conn.commit()

        cursor = await conn.execute("SELECT COUNT(*) FROM saved_cards WHERE user_id = 'user1'")
        row = await cursor.fetchone()
        assert row[0] == 1

        await conn.execute("DELETE FROM users WHERE id = 'user1'")
        await conn.commit()

        cursor = await conn.execute("SELECT COUNT(*) FROM saved_cards WHERE user_id = 'user1'")
        row = await cursor.fetchone()
        assert row[0] == 0
