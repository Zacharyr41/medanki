import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from medanki.models.cards import ClozeCard, VignetteCard


class ValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ValidationResult:
    status: ValidationStatus
    issues: list[str] = field(default_factory=list)
    confidence: float | None = None


@dataclass
class ClozeCardInput:
    text: str
    source_chunk: str
    metadata: dict[str, Any] | None = None


@dataclass
class VignetteCardInput:
    stem: str
    options: list[str]
    correct_answer: str
    source_chunk: str
    metadata: dict[str, Any] | None = None


class ILLMClient(Protocol):
    async def check_accuracy(self, claim: str) -> dict[str, Any]: ...
    async def check_grounding(self, claim: str, source: str) -> dict[str, Any]: ...


class CardValidator:
    CLOZE_PATTERN = re.compile(r"\{\{c\d+::([^}]+)\}\}")
    MALFORMED_CLOZE_PATTERN = re.compile(r"\{\{c\d+:[^:][^}]*\}\}")
    MAX_ANSWER_WORDS = 4
    CONFIDENCE_THRESHOLD = 0.7
    VALID_ANSWERS = {"A", "B", "C", "D", "E"}

    def __init__(self, llm_client: ILLMClient | None = None):
        self.llm_client = llm_client

    async def validate(
        self,
        card: "ClozeCard | VignetteCard",
        source_content: str | None = None,
    ) -> tuple[bool, list[str]]:
        from medanki.models.cards import ClozeCard, VignetteCard

        issues: list[str] = []

        if isinstance(card, ClozeCard):
            matches = self.CLOZE_PATTERN.findall(card.text)
            if not matches:
                issues.append("No valid cloze deletion found")
            for match in matches:
                word_count = len(match.split())
                if word_count > self.MAX_ANSWER_WORDS:
                    issues.append(f"Cloze answer too long: {word_count} words")
        elif isinstance(card, VignetteCard):
            if len(card.options) < 2:
                issues.append("Vignette must have at least 2 options")
            if card.answer.upper() not in self.VALID_ANSWERS:
                issues.append(f"Invalid answer '{card.answer}'")

        return len(issues) == 0, issues

    def validate_schema(self, card: ClozeCardInput | VignetteCardInput) -> ValidationResult:
        if isinstance(card, ClozeCardInput):
            return self._validate_cloze_schema(card)
        elif isinstance(card, VignetteCardInput):
            return self._validate_vignette_schema(card)
        return ValidationResult(status=ValidationStatus.INVALID, issues=["Unknown card type"])

    def _validate_cloze_schema(self, card: ClozeCardInput) -> ValidationResult:
        issues = []

        if self.MALFORMED_CLOZE_PATTERN.search(card.text):
            issues.append("Malformed cloze syntax: missing double colon (::)")
            return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        matches = self.CLOZE_PATTERN.findall(card.text)
        if not matches:
            issues.append("No valid cloze deletion found in card text")
            return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        for match in matches:
            word_count = len(match.split())
            if word_count > self.MAX_ANSWER_WORDS:
                issues.append(
                    f"Cloze answer too long: {word_count} words (max {self.MAX_ANSWER_WORDS})"
                )
                return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        return ValidationResult(status=ValidationStatus.VALID)

    def _validate_vignette_schema(self, card: VignetteCardInput) -> ValidationResult:
        issues = []

        if len(card.options) < 5:
            issues.append(f"Vignette must have at least 5 options, found {len(card.options)}")
            return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        if card.correct_answer not in self.VALID_ANSWERS:
            issues.append(f"Invalid answer '{card.correct_answer}': must be A-E")
            return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        return ValidationResult(status=ValidationStatus.VALID)

    async def validate_accuracy(self, card: ClozeCardInput | VignetteCardInput) -> ValidationResult:
        if not self.llm_client:
            return ValidationResult(
                status=ValidationStatus.NEEDS_REVIEW,
                issues=["No LLM client configured for accuracy validation"],
            )

        text = card.text if isinstance(card, ClozeCardInput) else card.stem
        result = await self.llm_client.check_accuracy(text)

        confidence = result.get("confidence", 0.0)
        is_accurate = result.get("is_accurate", False)

        if not is_accurate:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                issues=["Medical claim is inaccurate or incorrect"],
                confidence=confidence,
            )

        if confidence < self.CONFIDENCE_THRESHOLD:
            return ValidationResult(
                status=ValidationStatus.NEEDS_REVIEW,
                issues=["Low confidence in accuracy assessment"],
                confidence=confidence,
            )

        return ValidationResult(status=ValidationStatus.VALID, confidence=confidence)

    async def validate_grounding(
        self, card: ClozeCardInput | VignetteCardInput
    ) -> ValidationResult:
        if not self.llm_client:
            return ValidationResult(
                status=ValidationStatus.NEEDS_REVIEW,
                issues=["No LLM client configured for grounding validation"],
            )

        text = card.text if isinstance(card, ClozeCardInput) else card.stem
        source = card.source_chunk

        result = await self.llm_client.check_grounding(text, source)

        is_grounded = result.get("is_grounded", False)
        explanation = result.get("explanation", "")

        if not is_grounded:
            issue = "Claim not grounded in source"
            if "mismatch" in explanation.lower():
                issue = "Entity mismatch between card and source"
            return ValidationResult(status=ValidationStatus.INVALID, issues=[issue])

        return ValidationResult(status=ValidationStatus.VALID)
