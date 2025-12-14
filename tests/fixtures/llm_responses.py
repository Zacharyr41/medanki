from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


def create_mock_message_response(
    text: str,
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> MagicMock:
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    mock_response.usage.input_tokens = input_tokens
    mock_response.usage.output_tokens = output_tokens
    return mock_response


SIMPLE_RESPONSE = {
    "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello! How can I help you today?"}],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 10, "output_tokens": 8},
}

STRUCTURED_RESPONSE_CONTENT = {
    "name": "test_item",
    "value": 42,
}

RATE_LIMIT_ERROR_RESPONSE: dict[str, Any] = {
    "type": "error",
    "error": {
        "type": "rate_limit_error",
        "message": "Rate limit exceeded. Please retry after 60 seconds.",
    },
}

API_ERROR_RESPONSE: dict[str, Any] = {
    "type": "error",
    "error": {
        "type": "api_error",
        "message": "Internal server error",
    },
}

OVERLOADED_ERROR_RESPONSE: dict[str, Any] = {
    "type": "error",
    "error": {
        "type": "overloaded_error",
        "message": "Anthropic's API is temporarily overloaded.",
    },
}
