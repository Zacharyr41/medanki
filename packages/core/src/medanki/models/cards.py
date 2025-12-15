from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar
from uuid import UUID, uuid4


class CardType(Enum):
    CLOZE = "cloze"
    VIGNETTE = "vignette"


class ValidationError(Exception):
    pass


@dataclass
class ClozeCard:
    text: str
    source_chunk_id: UUID
    topic_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    card_type: ClassVar[CardType] = CardType.CLOZE

    CLOZE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")
    MAX_ANSWER_WORDS: ClassVar[int] = 4

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        cloze_matches = list(self.CLOZE_PATTERN.finditer(self.text))
        if not cloze_matches:
            raise ValidationError(
                "Cloze card must contain at least one cloze deletion in {{c1::answer}} format"
            )

        indices: list[int] = []
        for match in cloze_matches:
            index = int(match.group(1))
            answer = match.group(2).strip()

            if index < 1:
                raise ValidationError(f"Cloze index must be >= 1, got {index}")
            indices.append(index)

            word_count = len(answer.split())
            if word_count < 1 or word_count > self.MAX_ANSWER_WORDS:
                raise ValidationError(
                    f"Cloze answer must be 1-{self.MAX_ANSWER_WORDS} words, got {word_count}: '{answer}'"
                )

        indices.sort()
        expected = list(range(1, len(indices) + 1))
        if indices != expected:
            raise ValidationError(
                f"Cloze indices must be sequential starting from 1, got {indices}"
            )

    @property
    def cloze_count(self) -> int:
        return len(self.CLOZE_PATTERN.findall(self.text))

    def get_answers(self) -> list[str]:
        return [match.group(2).strip() for match in self.CLOZE_PATTERN.finditer(self.text)]


@dataclass
class VignetteOption:
    letter: str
    text: str


@dataclass
class VignetteCard:
    stem: str
    question: str
    options: list[VignetteOption]
    answer: str
    explanation: str
    source_chunk_id: UUID
    topic_id: str | None = None
    id: UUID = field(default_factory=uuid4)
    card_type: ClassVar[CardType] = CardType.VIGNETTE

    VALID_ANSWER_LETTERS: ClassVar[set[str]] = {"A", "B", "C", "D", "E"}
    MAX_ANSWER_WORDS: ClassVar[int] = 4

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.stem or not self.stem.strip():
            raise ValidationError("Vignette stem cannot be empty")

        if not self.question or not self.question.strip():
            raise ValidationError("Vignette question cannot be empty")

        if len(self.options) < 2:
            raise ValidationError("Vignette must have at least 2 options")

        if len(self.options) > 5:
            raise ValidationError("Vignette must have at most 5 options")

        option_letters = {opt.letter.upper() for opt in self.options}
        expected_letters = {chr(ord("A") + i) for i in range(len(self.options))}
        if option_letters != expected_letters:
            raise ValidationError(
                f"Option letters must be sequential starting from A, got {sorted(option_letters)}"
            )

        for opt in self.options:
            if not opt.text or not opt.text.strip():
                raise ValidationError(f"Option {opt.letter} text cannot be empty")

        answer_upper = self.answer.upper()
        if answer_upper not in option_letters:
            raise ValidationError(
                f"Answer '{self.answer}' must be one of the option letters: {sorted(option_letters)}"
            )

        correct_option = next(opt for opt in self.options if opt.letter.upper() == answer_upper)
        answer_word_count = len(correct_option.text.split())
        if answer_word_count < 1 or answer_word_count > self.MAX_ANSWER_WORDS:
            raise ValidationError(
                f"Correct answer option must be 1-{self.MAX_ANSWER_WORDS} words, got {answer_word_count}"
            )

        if not self.explanation or not self.explanation.strip():
            raise ValidationError("Vignette explanation cannot be empty")

    def get_correct_option(self) -> VignetteOption:
        answer_upper = self.answer.upper()
        return next(opt for opt in self.options if opt.letter.upper() == answer_upper)
