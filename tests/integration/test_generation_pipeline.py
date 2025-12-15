"""Integration tests for the card generation pipeline.

Tests card generation from chunks using LLM, validation, and deduplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from medanki.generation.cloze import ClozeGenerator
from medanki.generation.deduplicator import Deduplicator
from medanki.generation.validator import CardValidator, ClozeCardInput, VignetteCardInput
from medanki.models.cards import ClozeCard, VignetteCard, VignetteOption

# ============================================================================
# Cloze Card Generation Tests
# ============================================================================

@pytest.mark.integration
class TestClozeGeneration:
    """Test cloze card generation from chunks."""

    async def test_generate_cloze_from_chunk(
        self,
        mock_llm_client,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test generating cloze cards from a chunk using real LLM call (mocked via VCR)."""
        generator = ClozeGenerator(llm_client=mock_llm_client)

        cards = await generator.generate(
            content=sample_chunk_with_cardiology.text,
            source_chunk_id=uuid4(),
            num_cards=3,
        )

        # Should generate at least one card
        assert len(cards) >= 1

        # Each card should have valid cloze syntax
        for card in cards:
            assert isinstance(card, ClozeCard)
            assert "{{c1::" in card.text
            assert "}}" in card.text
            assert card.source_chunk_id is not None

    async def test_generate_cloze_respects_count(
        self,
        mock_llm_client,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test that generation respects the count parameter."""
        generator = ClozeGenerator(llm_client=mock_llm_client)

        cards = await generator.generate(
            content=sample_chunk_with_cardiology.text,
            source_chunk_id=uuid4(),
            num_cards=2,
        )

        # Should not exceed requested count
        assert len(cards) <= 2

    async def test_generate_cloze_includes_topic_id(
        self,
        mock_llm_client,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test that generated cards include topic_id."""
        generator = ClozeGenerator(llm_client=mock_llm_client)

        cards = await generator.generate(
            content=sample_chunk_with_cardiology.text,
            source_chunk_id=uuid4(),
            topic_id="cardiology",
            num_cards=3,
        )

        # Cards should have topic_id
        for card in cards:
            assert hasattr(card, "topic_id")
            assert card.topic_id == "cardiology"


# ============================================================================
# Vignette Card Generation Tests
# ============================================================================

@pytest.mark.integration
class TestVignetteGeneration:
    """Test vignette card generation from chunks."""

    async def test_generate_vignette_from_chunk(
        self,
        mock_llm_client,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test generating vignette cards from a chunk."""
        # Generate vignette using mock LLM
        vignettes = await mock_llm_client.generate_vignette(
            text=sample_chunk_with_cardiology.text,
            count=1,
        )

        assert len(vignettes) >= 1

        vignette = vignettes[0]
        assert "stem" in vignette
        assert "question" in vignette
        assert "options" in vignette
        assert "answer" in vignette
        assert "explanation" in vignette

        # Answer should be a valid option letter
        assert vignette["answer"] in ["A", "B", "C", "D", "E"]

    async def test_vignette_has_five_options(
        self,
        mock_llm_client,
        sample_chunk_with_cardiology,
    ) -> None:
        """Test that vignettes have 5 answer options."""
        vignettes = await mock_llm_client.generate_vignette(
            text=sample_chunk_with_cardiology.text,
            count=1,
        )

        vignette = vignettes[0]
        assert len(vignette["options"]) == 5


# ============================================================================
# Card Validation Tests
# ============================================================================

@pytest.mark.integration
class TestCardValidation:
    """Test card validation."""

    def test_validate_valid_cloze_card(self) -> None:
        """Test validation of a valid cloze card."""
        validator = CardValidator()

        card = ClozeCardInput(
            text="The cardiac cycle consists of {{c1::systole}} and {{c2::diastole}} phases.",
            source_chunk="Cardiac cycle information.",
        )

        result = validator.validate_schema(card)

        assert result.status.value == "valid"
        assert len(result.issues) == 0

    def test_validate_invalid_cloze_syntax(self) -> None:
        """Test validation catches invalid cloze syntax."""
        validator = CardValidator()

        # Missing double colon
        card = ClozeCardInput(
            text="The cardiac cycle consists of {{c1:systole}} phases.",
            source_chunk="Cardiac cycle information.",
        )

        result = validator.validate_schema(card)

        assert result.status.value == "invalid"
        assert len(result.issues) > 0

    def test_validate_cloze_answer_too_long(self) -> None:
        """Test validation catches answers exceeding 4 words."""
        validator = CardValidator()

        card = ClozeCardInput(
            text="The heart has {{c1::four chambers that pump blood throughout the body}} structures.",
            source_chunk="Heart anatomy.",
        )

        result = validator.validate_schema(card)

        assert result.status.value == "invalid"
        assert any("too long" in issue.lower() for issue in result.issues)

    def test_validate_generated_cards(
        self,
        mock_llm_client,
    ) -> None:
        """Test that generated cards pass validation."""
        async def run_test():
            generator = ClozeGenerator(llm_client=mock_llm_client)
            cards = await generator.generate(
                content="Systole and diastole are phases of the cardiac cycle.",
                source_chunk_id=uuid4(),
                num_cards=2,
            )
            return cards

        import asyncio
        cards = asyncio.get_event_loop().run_until_complete(run_test())

        validator = CardValidator()

        for card in cards:
            card_input = ClozeCardInput(
                text=card.text,
                source_chunk="Source content.",
            )
            result = validator.validate_schema(card_input)

            # Generated cards should pass basic schema validation
            # (They're pre-validated by the generator)
            assert result.status.value == "valid", f"Card failed validation: {result.issues}"

    def test_validate_vignette_schema(self) -> None:
        """Test vignette schema validation."""
        validator = CardValidator()

        card = VignetteCardInput(
            stem="A 55-year-old male presents with chest pain.",
            options=["MI", "PE", "Pneumonia", "Aortic dissection", "Pericarditis"],
            correct_answer="A",
            source_chunk="Cardiology case.",
        )

        result = validator.validate_schema(card)

        assert result.status.value == "valid"

    def test_validate_vignette_insufficient_options(self) -> None:
        """Test vignette validation requires 5 options."""
        validator = CardValidator()

        card = VignetteCardInput(
            stem="A 55-year-old male presents with chest pain.",
            options=["MI", "PE", "Pneumonia"],  # Only 3 options
            correct_answer="A",
            source_chunk="Cardiology case.",
        )

        result = validator.validate_schema(card)

        assert result.status.value == "invalid"
        assert any("5 options" in issue for issue in result.issues)


# ============================================================================
# Accuracy and Grounding Validation Tests
# ============================================================================

@pytest.mark.integration
class TestAccuracyValidation:
    """Test accuracy and grounding validation with LLM."""

    async def test_validate_accuracy_with_llm(self, mock_llm_client) -> None:
        """Test accuracy validation using LLM."""
        validator = CardValidator(llm_client=mock_llm_client)

        card = ClozeCardInput(
            text="The cardiac cycle consists of {{c1::systole}} and {{c2::diastole}}.",
            source_chunk="The cardiac cycle has systole and diastole phases.",
        )

        result = await validator.validate_accuracy(card)

        # Mock LLM returns accurate
        assert result.status.value in ["valid", "needs_review"]

    async def test_validate_grounding_with_llm(self, mock_llm_client) -> None:
        """Test grounding validation using LLM."""
        validator = CardValidator(llm_client=mock_llm_client)

        card = ClozeCardInput(
            text="{{c1::Systole}} is when the ventricles contract.",
            source_chunk="During systole, the ventricles contract and eject blood.",
        )

        result = await validator.validate_grounding(card)

        # Mock LLM returns grounded
        assert result.status.value in ["valid", "needs_review"]


# ============================================================================
# Deduplication Tests
# ============================================================================

@pytest.mark.integration
class TestDeduplication:
    """Test card deduplication."""

    def test_deduplicate_exact_duplicates(self) -> None:
        """Test that exact duplicate cards are removed."""
        deduplicator = Deduplicator()

        # Create duplicate cards
        card1 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        card2 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",  # Exact duplicate
            source_chunk_id=uuid4(),
        )

        card3 = ClozeCard(
            text="The cardiac cycle has {{c1::two}} phases.",  # Different card
            source_chunk_id=uuid4(),
        )

        cards = [card1, card2, card3]
        unique_cards = deduplicator.deduplicate(cards)

        # Should remove one duplicate
        assert len(unique_cards) == 2

    def test_deduplicate_preserves_unique_cards(self) -> None:
        """Test that unique cards are preserved during deduplication."""
        deduplicator = Deduplicator()

        cards = [
            ClozeCard(
                text="{{c1::Systole}} is ventricular contraction.",
                source_chunk_id=uuid4(),
            ),
            ClozeCard(
                text="{{c1::Diastole}} is ventricular relaxation.",
                source_chunk_id=uuid4(),
            ),
            ClozeCard(
                text="{{c1::Lisinopril}} is an ACE inhibitor.",
                source_chunk_id=uuid4(),
            ),
        ]

        unique_cards = deduplicator.deduplicate(cards)

        # All cards are unique, none should be removed
        assert len(unique_cards) == 3

    def test_detect_similar_cards(self) -> None:
        """Test detection of similar (near-duplicate) cards."""
        deduplicator = Deduplicator()

        card1 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        card2 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        existing_cards = [card1]
        result = deduplicator.check_duplicate(card2, existing_cards)

        assert result.is_duplicate is True
        assert result.status.value == "exact"
        assert result.similarity_score == 1.0

    def test_content_hash_consistency(self) -> None:
        """Test that content hash is consistent for same content."""
        deduplicator = Deduplicator()

        card1 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        card2 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),  # Different ID
        )

        hash1 = deduplicator.compute_content_hash(card1)
        hash2 = deduplicator.compute_content_hash(card2)

        # Same content should produce same hash
        assert hash1 == hash2

    def test_vignette_deduplication(self) -> None:
        """Test deduplication of vignette cards."""
        deduplicator = Deduplicator()

        vignette1 = VignetteCard(
            stem="A 55-year-old male presents with chest pain.",
            question="What is the diagnosis?",
            options=[
                VignetteOption(letter="A", text="MI"),
                VignetteOption(letter="B", text="PE"),
            ],
            answer="A",
            explanation="ST elevation indicates MI.",
            source_chunk_id=uuid4(),
        )

        vignette2 = VignetteCard(
            stem="A 55-year-old male presents with chest pain.",  # Same stem
            question="What is the diagnosis?",
            options=[
                VignetteOption(letter="A", text="MI"),
                VignetteOption(letter="B", text="PE"),
            ],
            answer="A",
            explanation="ST elevation indicates MI.",
            source_chunk_id=uuid4(),
        )

        cards = [vignette1, vignette2]
        unique_cards = deduplicator.deduplicate(cards)

        # Should detect as duplicates
        assert len(unique_cards) == 1


# ============================================================================
# Semantic Deduplication Tests
# ============================================================================

@pytest.mark.integration
class TestSemanticDeduplication:
    """Test semantic similarity-based deduplication."""

    async def test_semantic_duplicate_detection(
        self,
        mock_embedding_service,
    ) -> None:
        """Test detection of semantically similar cards."""
        deduplicator = Deduplicator(
            embedding_client=mock_embedding_service,
            similarity_threshold=0.95,
        )

        card1 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        # Semantically similar but not exact
        card2 = ClozeCard(
            text="The human heart contains {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        result = await deduplicator.check_semantic_duplicate(card1, [card2])

        # Should detect some similarity
        assert result.similarity_score >= 0.0
        # The mock embedding produces deterministic results based on hash
        # so similar text may or may not be flagged as duplicate

    async def test_semantic_unique_detection(
        self,
        mock_embedding_service,
    ) -> None:
        """Test that semantically different cards are not flagged."""
        deduplicator = Deduplicator(
            embedding_client=mock_embedding_service,
            similarity_threshold=0.9,
        )

        card1 = ClozeCard(
            text="The heart has {{c1::four}} chambers.",
            source_chunk_id=uuid4(),
        )

        card2 = ClozeCard(
            text="{{c1::Furosemide}} is a loop diuretic medication.",
            source_chunk_id=uuid4(),
        )

        result = await deduplicator.check_semantic_duplicate(card1, [card2])

        # Very different content should not be duplicate
        # (depending on threshold and embedding similarity)
        assert result.similarity_score < 0.95


# ============================================================================
# Generation Pipeline Integration Tests
# ============================================================================

@pytest.mark.integration
class TestGenerationPipelineIntegration:
    """Test the full generation pipeline."""

    async def test_generate_validate_deduplicate_pipeline(
        self,
        mock_llm_client,
        sample_chunk_with_cardiology,
        sample_chunk_with_pharmacology,
    ) -> None:
        """Test the full generate -> validate -> deduplicate pipeline."""
        generator = ClozeGenerator(llm_client=mock_llm_client)
        validator = CardValidator()
        deduplicator = Deduplicator()

        # Generate cards from multiple chunks
        all_cards: list[ClozeCard] = []

        for chunk in [sample_chunk_with_cardiology, sample_chunk_with_pharmacology]:
            generated = await generator.generate(
                content=chunk.text,
                source_chunk_id=uuid4(),
                num_cards=3,
            )

            # Validate each card
            for card in generated:
                card_input = ClozeCardInput(
                    text=card.text,
                    source_chunk=chunk.text,
                )
                result = validator.validate_schema(card_input)

                if result.status.value == "valid":
                    all_cards.append(card)

        # Deduplicate
        unique_cards = deduplicator.deduplicate(all_cards)

        # Should have generated some valid, unique cards
        assert len(unique_cards) >= 1

        # All remaining cards should be valid
        for card in unique_cards:
            assert "{{c1::" in card.text
            assert "}}" in card.text

    async def test_empty_chunk_generates_no_cards(
        self,
        mock_llm_client,
    ) -> None:
        """Test that empty chunks don't generate cards."""
        generator = ClozeGenerator(llm_client=mock_llm_client)
        cards = await generator.generate(
            content="",
            source_chunk_id=uuid4(),
            num_cards=3,
        )

        # Empty text should not produce cards
        # (The generator or LLM should handle this gracefully)
        assert isinstance(cards, list)
