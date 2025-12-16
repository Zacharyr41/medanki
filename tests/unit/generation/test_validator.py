from unittest.mock import AsyncMock, MagicMock

import pytest

from medanki.generation.validator import (
    CardValidator,
    ValidationStatus,
)
from medanki.generation.validator import (
    ClozeCardInput as ClozeCard,
)
from medanki.generation.validator import (
    VignetteCardInput as VignetteCard,
)


class TestClozeSchemaValidation:
    def test_valid_cloze_passes(self):
        validator = CardValidator()
        card = ClozeCard(
            text="The {{c1::mitochondria}} is the powerhouse of the cell.",
            source_chunk="The mitochondria is the powerhouse of the cell.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.VALID
        assert len(result.issues) == 0

    def test_missing_cloze_fails(self):
        validator = CardValidator()
        card = ClozeCard(
            text="The mitochondria is the powerhouse of the cell.",
            source_chunk="The mitochondria is the powerhouse of the cell.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.INVALID
        assert any("cloze" in issue.lower() for issue in result.issues)

    def test_malformed_cloze_fails(self):
        validator = CardValidator()
        card = ClozeCard(
            text="The {{c1: mitochondria}} is the powerhouse of the cell.",
            source_chunk="The mitochondria is the powerhouse of the cell.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.INVALID
        assert any(
            "malformed" in issue.lower() or "syntax" in issue.lower() for issue in result.issues
        )

    def test_answer_too_long_fails(self):
        validator = CardValidator()
        card = ClozeCard(
            text="CHF is treated with {{c1::ACE inhibitors beta blockers diuretics and aldosterone antagonists together}}.",
            source_chunk="CHF is treated with ACE inhibitors beta blockers diuretics and aldosterone antagonists together.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.INVALID
        assert any("long" in issue.lower() or "word" in issue.lower() for issue in result.issues)


class TestVignetteAgeValidation:
    """Tests for vignette age validation."""

    def test_validate_vignette_without_age_passes_basic_schema(self):
        """Vignette without patient age passes basic schema validation (age check is separate concern)."""
        validator = CardValidator()
        card = VignetteCard(
            stem="A male patient presents with chest pain. Which is the most likely diagnosis?",
            options=["A. MI", "B. PE", "C. Pneumonia", "D. GERD", "E. Costochondritis"],
            correct_answer="A",
            source_chunk="Chest pain is often MI.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.VALID


class TestVignetteSchemaValidation:
    def test_valid_vignette_passes(self):
        validator = CardValidator()
        card = VignetteCard(
            stem="A 45-year-old male presents with chest pain. Which is the most likely diagnosis?",
            options=["A. MI", "B. PE", "C. Pneumonia", "D. GERD", "E. Costochondritis"],
            correct_answer="A",
            source_chunk="Chest pain in middle-aged men is often MI.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.VALID
        assert len(result.issues) == 0

    def test_vignette_missing_options_fails(self):
        validator = CardValidator()
        card = VignetteCard(
            stem="A 45-year-old male presents with chest pain. Which is the most likely diagnosis?",
            options=["A. MI", "B. PE", "C. Pneumonia"],
            correct_answer="A",
            source_chunk="Chest pain in middle-aged men is often MI.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.INVALID
        assert any("option" in issue.lower() or "5" in issue for issue in result.issues)

    def test_vignette_invalid_answer_fails(self):
        validator = CardValidator()
        card = VignetteCard(
            stem="A 45-year-old male presents with chest pain. Which is the most likely diagnosis?",
            options=["A. MI", "B. PE", "C. Pneumonia", "D. GERD", "E. Costochondritis"],
            correct_answer="F",
            source_chunk="Chest pain in middle-aged men is often MI.",
        )

        result = validator.validate_schema(card)

        assert result.status == ValidationStatus.INVALID
        assert any("answer" in issue.lower() for issue in result.issues)


class TestMedicalAccuracyValidation:
    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.check_accuracy = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_accurate_claim_passes(self, mock_llm_client):
        mock_llm_client.check_accuracy.return_value = {
            "is_accurate": True,
            "confidence": 0.95,
            "explanation": "Statement is factually correct.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="The {{c1::left ventricle}} pumps blood to the systemic circulation.",
            source_chunk="The left ventricle pumps blood to the systemic circulation.",
        )

        result = await validator.validate_accuracy(card)

        assert result.status == ValidationStatus.VALID
        mock_llm_client.check_accuracy.assert_called_once()

    @pytest.mark.asyncio
    async def test_inaccurate_claim_fails(self, mock_llm_client):
        mock_llm_client.check_accuracy.return_value = {
            "is_accurate": False,
            "confidence": 0.92,
            "explanation": "The right ventricle pumps to pulmonary, not systemic.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="The {{c1::right ventricle}} pumps blood to the systemic circulation.",
            source_chunk="The right ventricle pumps blood to the systemic circulation.",
        )

        result = await validator.validate_accuracy(card)

        assert result.status == ValidationStatus.INVALID
        assert any(
            "inaccurate" in issue.lower() or "incorrect" in issue.lower() for issue in result.issues
        )

    @pytest.mark.asyncio
    async def test_returns_confidence_score(self, mock_llm_client):
        mock_llm_client.check_accuracy.return_value = {
            "is_accurate": True,
            "confidence": 0.87,
            "explanation": "Statement is correct.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="The {{c1::mitochondria}} produces ATP.",
            source_chunk="The mitochondria produces ATP.",
        )

        result = await validator.validate_accuracy(card)

        assert result.confidence is not None
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_flags_uncertain_claims(self, mock_llm_client):
        mock_llm_client.check_accuracy.return_value = {
            "is_accurate": True,
            "confidence": 0.55,
            "explanation": "Statement may be correct but requires verification.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="The {{c1::experimental drug X}} treats condition Y.",
            source_chunk="The experimental drug X treats condition Y.",
        )

        result = await validator.validate_accuracy(card)

        assert result.status == ValidationStatus.NEEDS_REVIEW
        assert result.confidence < 0.7


class TestHallucinationDetection:
    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.check_grounding = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_detects_unsupported_claim(self, mock_llm_client):
        mock_llm_client.check_grounding.return_value = {
            "is_grounded": False,
            "explanation": "Claim about dosage not found in source.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="Metformin is dosed at {{c1::500mg}} initially.",
            source_chunk="Metformin is used for type 2 diabetes management.",
        )

        result = await validator.validate_grounding(card)

        assert result.status == ValidationStatus.INVALID
        assert any(
            "unsupported" in issue.lower()
            or "grounded" in issue.lower()
            or "source" in issue.lower()
            for issue in result.issues
        )

    @pytest.mark.asyncio
    async def test_detects_entity_mismatch(self, mock_llm_client):
        mock_llm_client.check_grounding.return_value = {
            "is_grounded": False,
            "explanation": "Drug name mismatch: source says Metformin, card says Metoprolol.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="{{c1::Metoprolol}} is used for type 2 diabetes.",
            source_chunk="Metformin is used for type 2 diabetes management.",
        )

        result = await validator.validate_grounding(card)

        assert result.status == ValidationStatus.INVALID
        assert any(
            "mismatch" in issue.lower() or "entity" in issue.lower() or "source" in issue.lower()
            for issue in result.issues
        )

    @pytest.mark.asyncio
    async def test_allows_supported_claims(self, mock_llm_client):
        mock_llm_client.check_grounding.return_value = {
            "is_grounded": True,
            "explanation": "All claims are supported by the source text.",
        }

        validator = CardValidator(llm_client=mock_llm_client)
        card = ClozeCard(
            text="{{c1::Metformin}} is used for type 2 diabetes.",
            source_chunk="Metformin is used for type 2 diabetes management.",
        )

        result = await validator.validate_grounding(card)

        assert result.status == ValidationStatus.VALID
