from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from medanki.exceptions import LLMError
from medanki.services.llm import ClaudeClient, LLMClient
from pydantic import BaseModel

if TYPE_CHECKING:
    pass


class SampleResponse(BaseModel):
    name: str
    value: int


class TestClaudeClientInitialization:
    def test_claude_client_initializes(self) -> None:
        with patch("medanki.services.llm.anthropic.Anthropic"):
            client = ClaudeClient(api_key="test-api-key")
            assert isinstance(client, LLMClient)
            assert client.model == "claude-sonnet-4-20250514"

    def test_claude_client_initializes_with_custom_model(self) -> None:
        with patch("medanki.services.llm.anthropic.Anthropic"):
            client = ClaudeClient(api_key="test-api-key", model="claude-3-haiku-20240307")
            assert client.model == "claude-3-haiku-20240307"


class TestClaudeClientGenerate:
    @pytest.fixture
    def mock_anthropic(self) -> MagicMock:
        with patch("medanki.services.llm.anthropic.Anthropic") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def client(self, mock_anthropic: MagicMock) -> ClaudeClient:
        return ClaudeClient(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_generate_returns_string(
        self, client: ClaudeClient, mock_anthropic: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_anthropic.messages.create.return_value = mock_response

        result = await client.generate("Test prompt")

        assert result == "Generated response"
        mock_anthropic.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_structured_returns_model(
        self, client: ClaudeClient, mock_anthropic: MagicMock
    ) -> None:
        with patch("medanki.services.llm.instructor") as mock_instructor:
            mock_instructor_client = MagicMock()
            mock_instructor.from_anthropic.return_value = mock_instructor_client

            expected_response = SampleResponse(name="test", value=42)
            mock_instructor_client.messages.create.return_value = expected_response

            result = await client.generate_structured(
                prompt="Test prompt",
                response_model=SampleResponse,
            )

            assert result == expected_response
            assert result.name == "test"
            assert result.value == 42


class TestClaudeClientRetry:
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self) -> None:
        with patch("medanki.services.llm.anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client

            import anthropic

            rate_limit_error = anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limited"}},
            )

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Success after retry")]
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 5

            mock_client.messages.create.side_effect = [
                rate_limit_error,
                rate_limit_error,
                mock_response,
            ]

            client = ClaudeClient(api_key="test-api-key", max_retries=3)
            result = await client.generate("Test prompt")

            assert result == "Success after retry"
            assert mock_client.messages.create.call_count == 3


class TestClaudeClientTokenUsage:
    @pytest.mark.asyncio
    async def test_tracks_token_usage(self) -> None:
        with patch("medanki.services.llm.anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Response")]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 50

            mock_client.messages.create.return_value = mock_response

            client = ClaudeClient(api_key="test-api-key")

            assert client.total_usage.input_tokens == 0
            assert client.total_usage.output_tokens == 0

            await client.generate("Test prompt")

            assert client.total_usage.input_tokens == 100
            assert client.total_usage.output_tokens == 50

            mock_response.usage.input_tokens = 200
            mock_response.usage.output_tokens = 100
            await client.generate("Another prompt")

            assert client.total_usage.input_tokens == 300
            assert client.total_usage.output_tokens == 150


class TestClaudeClientErrorHandling:
    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self) -> None:
        with patch("medanki.services.llm.anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = MagicMock()
            mock_anthropic_cls.return_value = mock_client

            import anthropic

            api_error = anthropic.APIError(
                message="Internal server error",
                request=MagicMock(),
                body={"error": {"message": "Internal server error"}},
            )

            mock_client.messages.create.side_effect = api_error

            client = ClaudeClient(api_key="test-api-key", max_retries=1)

            with pytest.raises(LLMError) as exc_info:
                await client.generate("Test prompt")

            assert "Internal server error" in str(exc_info.value)


class TestLLMClientProtocol:
    def test_claude_client_implements_protocol(self) -> None:
        with patch("medanki.services.llm.anthropic.Anthropic"):
            client = ClaudeClient(api_key="test-api-key")
            assert isinstance(client, LLMClient)

    def test_protocol_has_required_methods(self) -> None:
        assert hasattr(LLMClient, "generate")
        assert hasattr(LLMClient, "generate_structured")
        assert hasattr(LLMClient, "total_usage")
