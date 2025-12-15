from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from medanki.generation.prompts.vignette_prompt import (
    QUESTION_TYPE_TEMPLATES,
    VIGNETTE_FEW_SHOT_EXAMPLES,
    VIGNETTE_SYSTEM_PROMPT,
)
from medanki.models.cards import VignetteCard, VignetteOption

if TYPE_CHECKING:
    from medanki.services.llm import LLMClient


class VignetteOptionResponse(BaseModel):
    letter: str = Field(description="Option letter (A, B, C, D, or E)")
    text: str = Field(description="Option text (1-4 words)")


class VignetteCardResponse(BaseModel):
    stem: str = Field(description="Clinical vignette stem with patient presentation")
    question: str = Field(description="Question being asked")
    options: list[VignetteOptionResponse] = Field(description="Five answer options A through E")
    answer: str = Field(description="Correct answer letter (A, B, C, D, or E)")
    explanation: str = Field(description="Explanation of the correct answer")


class VignetteGenerationResponse(BaseModel):
    cards: list[VignetteCardResponse] = Field(description="List of generated vignette cards")


QuestionType = Literal["diagnosis", "next_step", "mechanism"]
Difficulty = Literal["step1", "step2"]


@dataclass
class VignetteGenerator:
    llm_client: LLMClient

    async def generate(
        self,
        content: str,
        source_chunk_id: UUID,
        topic_id: str | None = None,
        question_type: QuestionType | None = None,
        difficulty: Difficulty = "step1",
        num_cards: int = 1,
    ) -> list[VignetteCard]:
        prompt = self._build_prompt(content, question_type, difficulty, num_cards)
        system = VIGNETTE_SYSTEM_PROMPT + "\n\n" + VIGNETTE_FEW_SHOT_EXAMPLES

        response = await self.llm_client.generate_structured(
            prompt=prompt,
            response_model=VignetteGenerationResponse,
            system=system,
        )

        return [
            VignetteCard(
                stem=card.stem,
                question=card.question,
                options=[VignetteOption(letter=opt.letter, text=opt.text) for opt in card.options],
                answer=card.answer,
                explanation=card.explanation,
                source_chunk_id=source_chunk_id,
                topic_id=topic_id,
            )
            for card in response.cards
        ]

    def _build_prompt(
        self,
        content: str,
        question_type: QuestionType | None,
        difficulty: Difficulty,
        num_cards: int,
    ) -> str:
        parts = [
            f"Generate {num_cards} USMLE-style clinical vignette question(s) based on the following medical content.",
            "",
            f"Difficulty level: {difficulty.upper()}",
        ]

        if question_type:
            question_template = QUESTION_TYPE_TEMPLATES.get(question_type, "")
            parts.append(f"Question type: {question_type}")
            parts.append(f'Use this question format: "{question_template}"')

        parts.extend(
            [
                "",
                "Content:",
                content,
                "",
                "Requirements:",
                "- Include patient demographics (age, sex)",
                "- Include relevant medical history",
                "- Include physical exam findings when appropriate",
                "- Include lab values with units when relevant",
                "- Create exactly 5 options (A through E)",
                "- Ensure distractors are plausible but distinguishable",
                "- Keep answer options to 1-4 words each",
            ]
        )

        return "\n".join(parts)
