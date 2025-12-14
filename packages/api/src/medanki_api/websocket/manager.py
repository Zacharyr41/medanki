from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        if job_id not in self._connections:
            self._connections[job_id] = []
        self._connections[job_id].append(websocket)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        if job_id in self._connections:
            if websocket in self._connections[job_id]:
                self._connections[job_id].remove(websocket)
            if not self._connections[job_id]:
                del self._connections[job_id]

    async def broadcast(self, job_id: str, message: dict[str, Any]) -> None:
        if job_id in self._connections:
            for websocket in self._connections[job_id]:
                await websocket.send_json(message)

    def has_connections(self, job_id: str) -> bool:
        return job_id in self._connections and len(self._connections[job_id]) > 0

    def connection_count(self, job_id: str) -> int:
        if job_id not in self._connections:
            return 0
        return len(self._connections[job_id])
