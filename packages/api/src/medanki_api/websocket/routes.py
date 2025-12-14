from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from medanki_api.websocket.manager import ConnectionManager

router = APIRouter()

_manager = ConnectionManager()

STAGES = ["ingesting", "chunking", "classifying", "generating", "exporting"]


@router.websocket("/api/ws/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    job_id: str,
) -> None:
    job_storage: dict[str, Any] = websocket.app.state.job_storage
    job = job_storage.get(job_id)

    if job is None:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()
    await _manager.connect(job_id, websocket)

    try:
        if job.get("status") == "completed":
            await websocket.send_json({
                "type": "complete",
                "progress": 100,
            })
            return

        job["status"] = "processing"
        job["stage"] = "ingesting"
        job["progress"] = 0

        for stage_idx, stage in enumerate(STAGES):
            job["stage"] = stage
            base_progress = (stage_idx / len(STAGES)) * 100

            for step in range(10):
                if websocket.client_state != WebSocketState.CONNECTED:
                    return

                step_progress = (step + 1) / 10
                job["progress"] = base_progress + (step_progress * (100 / len(STAGES)))

                await websocket.send_json({
                    "type": "progress",
                    "progress": job["progress"],
                    "stage": stage,
                })

                await asyncio.sleep(0.3)

        job["status"] = "completed"
        job["progress"] = 100

        await websocket.send_json({
            "type": "complete",
            "progress": 100,
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
            })
    finally:
        await _manager.disconnect(job_id, websocket)
