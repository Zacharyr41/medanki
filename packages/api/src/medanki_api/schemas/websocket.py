from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, field_validator


class WebSocketMessage(BaseModel):
    type: str


class ProgressMessage(WebSocketMessage):
    type: Literal["progress"] = "progress"
    progress: int
    stage: str
    details: dict[str, Any]

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v


class CompleteMessage(WebSocketMessage):
    type: Literal["complete"] = "complete"
    result: dict[str, Any]


class ErrorMessage(WebSocketMessage):
    type: Literal["error"] = "error"
    error: str
    details: dict[str, Any]
