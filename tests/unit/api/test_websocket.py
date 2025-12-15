from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

if TYPE_CHECKING:
    pass


class TestWebSocketConnection:
    @pytest.mark.asyncio
    async def test_websocket_connects(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from medanki_api.websocket.routes import router

        app = FastAPI()
        app.include_router(router)
        app.state.job_storage = {
            "job-123": {"status": "completed", "progress": 100, "cards_generated": 5}
        }

        with TestClient(app) as client:
            with client.websocket_connect("/api/ws/job-123") as websocket:
                assert websocket is not None
                data = websocket.receive_json()
                assert data["type"] == "complete"

    @pytest.mark.asyncio
    async def test_websocket_invalid_job_closes(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from starlette.websockets import WebSocketDisconnect

        from medanki_api.websocket.routes import router

        app = FastAPI()
        app.include_router(router)
        app.state.job_storage = {}

        with TestClient(app) as client, pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/ws/unknown-job"):
                pass

    @pytest.mark.asyncio
    async def test_websocket_sends_initial_status(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from medanki_api.websocket.routes import router

        app = FastAPI()
        app.include_router(router)
        app.state.job_storage = {
            "job-123": {"status": "completed", "progress": 100, "cards_generated": 10}
        }

        with TestClient(app) as client:
            with client.websocket_connect("/api/ws/job-123") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "complete"
                assert "progress" in data


class TestProgressUpdates:
    @pytest.mark.asyncio
    async def test_receives_progress_updates(self) -> None:
        from medanki_api.websocket.manager import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        await manager.connect("job-123", mock_websocket)
        await manager.broadcast(
            "job-123", {"type": "progress", "progress": 50, "stage": "generating"}
        )

        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_progress_has_percentage(self) -> None:
        from medanki_api.schemas.websocket import ProgressMessage

        message = ProgressMessage(type="progress", progress=75, stage="generating", details={})
        assert message.progress == 75
        assert 0 <= message.progress <= 100

    @pytest.mark.asyncio
    async def test_progress_has_stage(self) -> None:
        from medanki_api.schemas.websocket import ProgressMessage

        message = ProgressMessage(type="progress", progress=50, stage="chunking", details={})
        assert message.stage == "chunking"

    @pytest.mark.asyncio
    async def test_progress_has_details(self) -> None:
        from medanki_api.schemas.websocket import ProgressMessage

        details = {"chunks_processed": 5, "total_chunks": 10}
        message = ProgressMessage(type="progress", progress=50, stage="chunking", details=details)
        assert message.details == details
        assert message.details["chunks_processed"] == 5


class TestMessageFormat:
    def test_message_is_json(self) -> None:
        from medanki_api.schemas.websocket import ProgressMessage

        message = ProgressMessage(type="progress", progress=50, stage="generating", details={})
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_message_has_type(self) -> None:
        from medanki_api.schemas.websocket import (
            CompleteMessage,
            ErrorMessage,
            ProgressMessage,
        )

        progress = ProgressMessage(type="progress", progress=50, stage="generating", details={})
        assert progress.type == "progress"

        complete = CompleteMessage(
            type="complete", result={"card_count": 10, "deck_path": "/path/to/deck.apkg"}
        )
        assert complete.type == "complete"

        error = ErrorMessage(type="error", error="Something went wrong", details={})
        assert error.type == "error"

    def test_progress_message_schema(self) -> None:
        from pydantic import ValidationError

        from medanki_api.schemas.websocket import ProgressMessage

        message = ProgressMessage(
            type="progress", progress=50, stage="ingesting", details={"file": "doc.pdf"}
        )
        assert message.type == "progress"
        assert message.progress == 50
        assert message.stage == "ingesting"
        assert message.details == {"file": "doc.pdf"}

        with pytest.raises(ValidationError):
            ProgressMessage(type="wrong", progress=50, stage="ingesting", details={})

    def test_complete_message_has_result(self) -> None:
        from medanki_api.schemas.websocket import CompleteMessage

        result = {"card_count": 25, "deck_path": "/output/anatomy.apkg"}
        message = CompleteMessage(type="complete", result=result)
        assert message.result["card_count"] == 25
        assert message.result["deck_path"] == "/output/anatomy.apkg"


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_error_message_on_failure(self) -> None:
        from medanki_api.schemas.websocket import ErrorMessage

        message = ErrorMessage(
            type="error",
            error="Generation failed",
            details={"reason": "API rate limit exceeded"},
        )
        assert message.type == "error"
        assert message.error == "Generation failed"
        assert message.details["reason"] == "API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_connection_closes_on_complete(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from medanki_api.websocket.routes import router

        app = FastAPI()
        app.include_router(router)
        app.state.job_storage = {
            "job-123": {
                "status": "completed",
                "progress": 100,
                "result": {"card_count": 10},
            }
        }

        with TestClient(app) as client:
            with client.websocket_connect("/api/ws/job-123") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "complete"

    @pytest.mark.asyncio
    async def test_handles_client_disconnect(self) -> None:
        from medanki_api.websocket.manager import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        await manager.connect("job-123", mock_websocket)
        assert manager.has_connections("job-123")

        await manager.disconnect("job-123", mock_websocket)
        assert not manager.has_connections("job-123")


class TestMultipleClients:
    @pytest.mark.asyncio
    async def test_multiple_clients_same_job(self) -> None:
        from medanki_api.websocket.manager import ConnectionManager

        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect("job-123", ws1)
        await manager.connect("job-123", ws2)

        assert manager.connection_count("job-123") == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_all_clients(self) -> None:
        from medanki_api.websocket.manager import ConnectionManager

        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect("job-123", ws1)
        await manager.connect("job-123", ws2)

        message = {"type": "progress", "progress": 50, "stage": "generating"}
        await manager.broadcast("job-123", message)

        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
