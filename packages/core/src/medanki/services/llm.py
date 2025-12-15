from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar, cast, runtime_checkable

import anthropic
import instructor
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from medanki.exceptions import LLMError
from medanki.generation.prompts.cloze_prompt import (
    CLOZE_FEW_SHOT_EXAMPLES,
    CLOZE_SYSTEM_PROMPT,
)

T = TypeVar("T", bound=BaseModel)


class ClozeCardResponse(BaseModel):
    text: str
    tags: list[str]


class ClozeGenerationResponse(BaseModel):
    cards: list[ClozeCardResponse]


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@runtime_checkable
class LLMClient(Protocol):
    @property
    def total_usage(self) -> TokenUsage: ...

    async def generate(self, prompt: str, system: str | None = None) -> str: ...

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system: str | None = None,
    ) -> T: ...


@dataclass
class ClaudeClient:
    api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_retries: int = 3
    max_tokens: int = 4096
    _client: anthropic.Anthropic = field(init=False, repr=False)
    _total_usage: TokenUsage = field(default_factory=TokenUsage, init=False)

    def __post_init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=self.api_key)

    @property
    def total_usage(self) -> TokenUsage:
        return self._total_usage

    async def generate(self, prompt: str, system: str | None = None) -> str:
        messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": prompt}]

        @retry(
            retry=retry_if_exception_type(anthropic.RateLimitError),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        )
        def _call_api() -> anthropic.types.Message:
            if system:
                return self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,
                    system=system,
                )
            return self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
            )

        try:
            response = await asyncio.to_thread(_call_api)
            self._total_usage.add(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            content = response.content[0]
            if hasattr(content, "text"):
                return str(content.text)
            raise LLMError("Unexpected response content type")
        except anthropic.RateLimitError:
            raise
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system: str | None = None,
    ) -> T:
        instructor_client = instructor.from_anthropic(self._client)

        @retry(
            retry=retry_if_exception_type(anthropic.RateLimitError),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        )
        def _call_api() -> Any:
            messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
            if system:
                return instructor_client.messages.create(
                    response_model=response_model,
                    messages=messages,  # type: ignore[arg-type]
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system,
                )
            return instructor_client.messages.create(
                response_model=response_model,
                messages=messages,  # type: ignore[arg-type]
                model=self.model,
                max_tokens=self.max_tokens,
            )

        try:
            result = await asyncio.to_thread(_call_api)
            return cast(T, result)
        except anthropic.RateLimitError:
            raise
        except anthropic.APIError as e:
            raise LLMError(str(e)) from e

    async def generate_cloze_cards(
        self,
        text: str,
        count: int = 3,
        tags: list[str] | None = None,
        topic_context: str | None = None,
    ) -> list[dict[str, Any]]:
        prompt = f"Generate {count} cloze deletion flashcards from the following medical text:\n\n{text}"
        if topic_context:
            prompt += f"\n\n{topic_context}\nFocus on concepts relevant to this topic area."
        if tags:
            prompt += f"\n\nSuggested tags: {', '.join(tags)}"

        system = CLOZE_SYSTEM_PROMPT + "\n\n" + CLOZE_FEW_SHOT_EXAMPLES
        response = await self.generate_structured(
            prompt=prompt,
            response_model=ClozeGenerationResponse,
            system=system,
        )
        return [{"text": card.text, "tags": card.tags} for card in response.cards]
