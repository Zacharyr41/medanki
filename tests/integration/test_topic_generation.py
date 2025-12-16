"""Integration tests for topic-based card generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for the FastAPI app."""
    from medanki_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestTopicJobCreation:
    """Test creating jobs from topic descriptions."""

    async def test_create_topic_job(self, client: AsyncClient) -> None:
        """Topic text creates a job with correct metadata."""
        from medanki_api.main import app

        data = {
            "topic_text": "I want to study cardiac arrhythmias",
            "exam": "USMLE Step 1",
            "card_types": "cloze,vignette",
            "max_cards": "25",
        }

        response = await client.post("/api/upload", data=data)

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        job = app.state.job_storage[job_id]
        assert job["input_type"] == "topic"
        assert job["topic_text"] == "I want to study cardiac arrhythmias"
        assert job["exam"] == "USMLE Step 1"
        assert job["card_types"] == "cloze,vignette"
        assert job["max_cards"] == 25

    async def test_topic_job_has_no_file_path(self, client: AsyncClient) -> None:
        """Topic jobs don't have file_path set."""
        from medanki_api.main import app

        data = {"topic_text": "Learn pharmacology"}

        response = await client.post("/api/upload", data=data)
        job_id = response.json()["job_id"]

        job = app.state.job_storage[job_id]
        assert job.get("file_path") is None


class TestLLMTopicGeneration:
    """Test the LLM topic generation method."""

    @pytest.mark.asyncio
    async def test_generate_cards_from_topic_returns_cards(self) -> None:
        """generate_cards_from_topic returns list of card dicts."""
        mock_response = AsyncMock()
        mock_response.cards = [
            type(
                "Card",
                (),
                {
                    "text": "The SA node is the {{c1::pacemaker}} of the heart.",
                    "tags": ["cardiology"],
                },
            )(),
            type(
                "Card",
                (),
                {
                    "text": "Atrial fibrillation is characterized by {{c1::irregular rhythm}}.",
                    "tags": ["cardiology"],
                },
            )(),
        ]

        with patch(
            "medanki.services.llm.ClaudeClient.generate_structured", return_value=mock_response
        ):
            from medanki.services.llm import ClaudeClient

            client = ClaudeClient(api_key="test-key")
            cards = await client.generate_cards_from_topic(
                topic_prompt="cardiac electrophysiology",
                count=5,
                exam_type="USMLE_STEP1",
            )

            assert len(cards) == 2
            assert cards[0]["text"] == "The SA node is the {{c1::pacemaker}} of the heart."
            assert "topic" in cards[0]

    @pytest.mark.asyncio
    async def test_generate_cards_from_topic_uses_exam_context(self) -> None:
        """Topic generation includes exam type in system prompt."""
        captured_system = None

        async def capture_generate_structured(prompt, response_model, system=None):
            nonlocal captured_system
            captured_system = system
            mock_response = type("Response", (), {"cards": []})()
            return mock_response

        with patch(
            "medanki.services.llm.ClaudeClient.generate_structured",
            side_effect=capture_generate_structured,
        ):
            from medanki.services.llm import ClaudeClient

            client = ClaudeClient(api_key="test-key")
            await client.generate_cards_from_topic(
                topic_prompt="renal physiology",
                count=5,
                exam_type="MCAT",
            )

            assert captured_system is not None
            assert "MCAT" in captured_system


class TestTopicGenerationPipeline:
    """Test the full topic generation pipeline."""

    @pytest.mark.asyncio
    async def test_topic_processing_skips_ingestion(self) -> None:
        """Topic jobs skip ingestion and chunking stages."""
        from starlette.websockets import WebSocket

        from medanki_api.websocket.routes import _process_topic_job

        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.client_state = type("State", (), {"CONNECTED": 1})()
        mock_ws.client_state = 1

        job = {
            "id": "test-job",
            "topic_text": "Learn about pharmacology",
            "exam": "USMLE_STEP1",
            "card_types": "cloze",
            "max_cards": 10,
        }

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            await _process_topic_job(mock_ws, job)

        assert "cards" in job
        assert job["cards_generated"] >= 0

    @pytest.mark.asyncio
    async def test_topic_processing_generates_cards_without_api_key(self) -> None:
        """Topic processing generates placeholder cards when no API key."""
        from starlette.websockets import WebSocket

        from medanki_api.websocket.routes import _process_topic_job

        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.client_state = 1

        job = {
            "id": "test-job",
            "topic_text": "Study cardiology basics",
            "exam": "MCAT",
            "card_types": "cloze",
            "max_cards": 5,
        }

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            await _process_topic_job(mock_ws, job)

        assert len(job["cards"]) == 5
        assert all(card["type"] == "cloze" for card in job["cards"])
        assert all("Study cardiology" in card["source_chunk"] for card in job["cards"])


class TestTopicVsFileProcessing:
    """Test that topic and file jobs are routed correctly."""

    @pytest.mark.asyncio
    async def test_process_job_routes_topic_jobs(self) -> None:
        """_process_job calls _process_topic_job for topic input_type."""
        from starlette.websockets import WebSocket

        from medanki_api.websocket.routes import _process_job

        mock_ws = AsyncMock(spec=WebSocket)

        topic_job = {
            "id": "topic-job",
            "input_type": "topic",
            "topic_text": "Test topic",
            "max_cards": 5,
        }

        with patch("medanki_api.websocket.routes._process_topic_job") as mock_topic:
            with patch("medanki_api.websocket.routes._process_file_job") as mock_file:
                mock_topic.return_value = None
                await _process_job(mock_ws, topic_job)

                mock_topic.assert_called_once()
                mock_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_job_routes_file_jobs(self) -> None:
        """_process_job calls _process_file_job for file input_type."""
        from starlette.websockets import WebSocket

        from medanki_api.websocket.routes import _process_job

        mock_ws = AsyncMock(spec=WebSocket)

        file_job = {
            "id": "file-job",
            "input_type": "file",
            "file_path": "/tmp/test.pdf",
        }

        with patch("medanki_api.websocket.routes._process_topic_job") as mock_topic:
            with patch("medanki_api.websocket.routes._process_file_job") as mock_file:
                mock_file.return_value = None
                await _process_job(mock_ws, file_job)

                mock_file.assert_called_once()
                mock_topic.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_job_defaults_to_file(self) -> None:
        """Jobs without input_type default to file processing."""
        from starlette.websockets import WebSocket

        from medanki_api.websocket.routes import _process_job

        mock_ws = AsyncMock(spec=WebSocket)

        legacy_job = {
            "id": "legacy-job",
            "file_path": "/tmp/test.pdf",
        }

        with patch("medanki_api.websocket.routes._process_topic_job") as mock_topic:
            with patch("medanki_api.websocket.routes._process_file_job") as mock_file:
                mock_file.return_value = None
                await _process_job(mock_ws, legacy_job)

                mock_file.assert_called_once()
                mock_topic.assert_not_called()
