from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from medanki_api.websocket.manager import ConnectionManager

router = APIRouter()

_manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    return _manager


def get_job_status(job_id: str) -> dict[str, Any] | None:
    return None


@router.websocket("/api/ws/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str,
    manager: ConnectionManager = Depends(get_manager),  # noqa: B008
) -> None:
    job_status = get_job_status(job_id)

    if job_status is None:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()
    await manager.connect(job_id, websocket)

    try:
        if job_status.get("status") == "completed":
            await websocket.send_json(
                {
                    "type": "complete",
                    "result": job_status.get("result", {}),
                }
            )
            return

        await websocket.send_json(
            {
                "type": "progress",
                "progress": job_status.get("progress", 0),
                "stage": job_status.get("stage", ""),
                "details": job_status.get("details", {}),
            }
        )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(job_id, websocket)
