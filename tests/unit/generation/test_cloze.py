"""Tests for cloze card generation service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from medanki.generation.cloze import ClozeGenerator


async def generate_from_chunk(generator: ClozeGenerator, chunk, count: int = 3):
    """Helper to call generator with new signature using chunk data."""
    return await generator.generate(
        content=chunk.text,
        source_chunk_id=chunk.id,
        num_cards=count,
    )


# Test fixtures and data classes for testing
@dataclass
class MockClassifiedChunk:
    """Mock classified chunk for testing."""

    id: UUID = field(default_factory=uuid4)
    document_id: UUID = field(default_factory=uuid4)
    text: str = ""
    topics: list[dict[str, str]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Create a mock LLM client that returns predefined card JSON."""
    client = AsyncMock()
    # Default response - a list of valid cloze cards
    client.generate_cloze_cards.return_value = [
        {
            "text": "The {{c1::mitochondria}} is the powerhouse of the cell.",
            "tags": ["biology", "cell-biology"],
        },
        {
            "text": "{{c1::ATP}} is produced through {{c2::oxidative phosphorylation}}.",
            "tags": ["biochemistry", "metabolism"],
        },
        {
            "text": "The {{c1::Krebs cycle}} occurs in the mitochondrial matrix.",
            "tags": ["biochemistry"],
        },
    ]
    return client


@pytest.fixture
def sample_classified_chunk() -> MockClassifiedChunk:
    """Create a sample classified chunk for testing."""
    return MockClassifiedChunk(
        text="""The mitochondria is often called the powerhouse of the cell because
        it produces ATP through oxidative phosphorylation. The Krebs cycle, also known
        as the citric acid cycle, occurs in the mitochondrial matrix and generates
        electron carriers for the electron transport chain.""",
        topics=[
            {"id": "1A", "path": "Biology > Cell Biology", "confidence": 0.85},
            {"id": "2B", "path": "Biochemistry > Metabolism", "confidence": 0.75},
        ],
        tags=["biology", "biochemistry", "cell-biology", "metabolism"],
    )


@pytest.fixture
def sample_pharmacology_chunk() -> MockClassifiedChunk:
    """Create a sample pharmacology chunk for testing."""
    return MockClassifiedChunk(
        text="""Metformin is a biguanide drug that is first-line treatment for
        type 2 diabetes mellitus. It works by decreasing hepatic glucose production
        and increasing insulin sensitivity in peripheral tissues. The drug class
        biguanides are known for their glucose-lowering effects without causing
        hypoglycemia.""",
        topics=[
            {"id": "PHARM1", "path": "Pharmacology > Endocrine", "confidence": 0.9},
        ],
        tags=["pharmacology", "endocrine", "diabetes"],
    )


@pytest.fixture
def sample_anatomy_chunk() -> MockClassifiedChunk:
    """Create a sample anatomy chunk for testing."""
    return MockClassifiedChunk(
        text="""The left anterior descending artery (LAD) is a major coronary artery
        that supplies blood to the anterior wall of the left ventricle. It originates
        from the left main coronary artery and travels in the anterior interventricular
        groove. Occlusion of the LAD can cause anterior myocardial infarction.""",
        topics=[
            {"id": "ANAT1", "path": "Anatomy > Cardiovascular", "confidence": 0.92},
        ],
        tags=["anatomy", "cardiovascular", "heart"],
    )


@pytest.fixture
def sample_biochemistry_chunk() -> MockClassifiedChunk:
    """Create a sample biochemistry chunk for testing."""
    return MockClassifiedChunk(
        text="""Glycolysis is the metabolic pathway that converts glucose into
        pyruvate. The rate-limiting enzyme is phosphofructokinase-1 (PFK-1), which
        catalyzes the phosphorylation of fructose-6-phosphate to fructose-1,6-bisphosphate.
        This enzyme is allosterically activated by AMP and inhibited by ATP and citrate.""",
        topics=[
            {
                "id": "BIOCHEM1",
                "path": "Biochemistry > Carbohydrate Metabolism",
                "confidence": 0.88,
            },
        ],
        tags=["biochemistry", "metabolism", "glycolysis"],
    )


@pytest.fixture
def cloze_generator(mock_llm_client: AsyncMock) -> ClozeGenerator:
    """Create a ClozeGenerator with mock LLM client."""
    from medanki.generation.cloze import ClozeGenerator

    return ClozeGenerator(llm_client=mock_llm_client)


class TestClozeCardGeneration:
    """Tests for basic cloze card generation functionality."""

    @pytest.mark.asyncio
    async def test_generates_cloze_cards(
        self, cloze_generator: ClozeGenerator, sample_classified_chunk: MockClassifiedChunk
    ) -> None:
        """Generation returns list of ClozeCard objects."""
        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        assert isinstance(cards, list)
        assert len(cards) > 0
        for card in cards:
            assert hasattr(card, "text")
            assert hasattr(card, "source_chunk_id")

    @pytest.mark.asyncio
    async def test_respects_count_parameter(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """count=3 parameter returns exactly 3 cards."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "Card {{c1::one}}.", "tags": []},
            {"text": "Card {{c1::two}}.", "tags": []},
            {"text": "Card {{c1::three}}.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk, count=3)

        assert len(cards) == 3

    @pytest.mark.asyncio
    async def test_cards_have_valid_cloze_syntax(
        self, cloze_generator: ClozeGenerator, sample_classified_chunk: MockClassifiedChunk
    ) -> None:
        """All generated cards have valid {{c1::...}} syntax."""
        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        cloze_pattern = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")
        for card in cards:
            matches = cloze_pattern.findall(card.text)
            assert len(matches) > 0, f"Card missing cloze deletion: {card.text}"

    @pytest.mark.asyncio
    async def test_answers_are_short(
        self, cloze_generator: ClozeGenerator, sample_classified_chunk: MockClassifiedChunk
    ) -> None:
        """Cloze answers are 1-4 words."""
        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        for card in cards:
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                word_count = len(answer.strip().split())
                assert 1 <= word_count <= 4, f"Answer '{answer}' has {word_count} words"

    @pytest.mark.asyncio
    async def test_cards_include_source_chunk_id(
        self, cloze_generator: ClozeGenerator, sample_classified_chunk: MockClassifiedChunk
    ) -> None:
        """Cards track provenance via source_chunk_id."""
        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        for card in cards:
            assert card.source_chunk_id == sample_classified_chunk.id

    @pytest.mark.asyncio
    async def test_cards_have_topic_id(
        self, cloze_generator: ClozeGenerator, sample_classified_chunk: MockClassifiedChunk
    ) -> None:
        """Cards have topic_id attribute."""
        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        for card in cards:
            assert hasattr(card, "topic_id")


class TestClozeContentQuality:
    """Tests for content quality of generated cloze cards."""

    @pytest.mark.asyncio
    async def test_extracts_key_concepts(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Cards cover main ideas from the source text."""
        # Mock LLM to return cards with key concepts
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "The {{c1::mitochondria}} is the powerhouse of the cell.", "tags": []},
            {"text": "{{c1::ATP}} is produced in mitochondria.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        # Check that key medical concepts are included in the cards
        all_text = " ".join(card.text for card in cards)
        assert any(
            concept in all_text.lower() for concept in ["mitochondria", "atp", "krebs", "oxidative"]
        )

    @pytest.mark.asyncio
    async def test_avoids_trivial_deletions(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters out trivial deletions like 'the', 'a', 'is'."""
        # Mock LLM returning cards with trivial deletions that should be filtered
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "{{c1::The}} cell produces energy.", "tags": []},  # Bad - trivial
            {"text": "The {{c1::mitochondria}} produces ATP.", "tags": []},  # Good
            {"text": "ATP {{c1::is}} important.", "tags": []},  # Bad - trivial
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        trivial_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "of",
            "to",
            "and",
            "or",
        }

        for card in cards:
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                # Single word answers should not be trivial
                if len(answer.split()) == 1:
                    assert answer.lower() not in trivial_words, f"Trivial deletion: {answer}"

    @pytest.mark.asyncio
    async def test_context_is_self_contained(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Each card makes sense on its own without additional context."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {
                "text": "The {{c1::mitochondria}} is the organelle that produces ATP in cells.",
                "tags": [],
            },
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        for card in cards:
            # Card should have enough context (minimum length)
            text_without_cloze = re.sub(r"\{\{c\d+::", "", card.text).replace("}}", "")
            assert len(text_without_cloze) >= 20, "Card lacks sufficient context"

    @pytest.mark.asyncio
    async def test_multiple_deletions_per_card(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Cards can have multiple cloze deletions {{c1::}} and {{c2::}}."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {
                "text": "{{c1::ATP}} is produced through {{c2::oxidative phosphorylation}}.",
                "tags": [],
            },
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        cloze_pattern = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")
        multi_deletion_card = cards[0]
        matches = cloze_pattern.findall(multi_deletion_card.text)

        assert len(matches) >= 2, "Card should have multiple deletions"
        indices = [int(m[0]) for m in matches]
        assert 1 in indices and 2 in indices, "Should have c1 and c2"


class TestTopicSpecificGeneration:
    """Tests for topic-specific card generation."""

    @pytest.mark.asyncio
    async def test_pharmacology_includes_drug_class(
        self,
        cloze_generator: ClozeGenerator,
        sample_pharmacology_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Pharmacology cards include drug class context."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {
                "text": "{{c1::Metformin}} is a biguanide used for type 2 diabetes.",
                "tags": ["pharmacology"],
            },
            {
                "text": "Biguanides like {{c1::metformin}} decrease hepatic glucose production.",
                "tags": ["pharmacology"],
            },
        ]

        cards = await generate_from_chunk(cloze_generator, sample_pharmacology_chunk)

        all_text = " ".join(card.text.lower() for card in cards)
        assert "biguanide" in all_text, "Pharmacology card should include drug class"

    @pytest.mark.asyncio
    async def test_anatomy_includes_location(
        self,
        cloze_generator: ClozeGenerator,
        sample_anatomy_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Anatomy cards have anatomical location context."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {
                "text": "The {{c1::LAD}} artery supplies the anterior wall of the left ventricle.",
                "tags": ["anatomy"],
            },
            {
                "text": "The LAD travels in the {{c1::anterior interventricular}} groove.",
                "tags": ["anatomy"],
            },
        ]

        cards = await generate_from_chunk(cloze_generator, sample_anatomy_chunk)

        all_text = " ".join(card.text.lower() for card in cards)
        location_terms = ["anterior", "left ventricle", "groove", "coronary", "interventricular"]
        has_location = any(term in all_text for term in location_terms)
        assert has_location, "Anatomy card should include location context"

    @pytest.mark.asyncio
    async def test_biochemistry_includes_pathway(
        self,
        cloze_generator: ClozeGenerator,
        sample_biochemistry_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Biochemistry cards preserve pathway context."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {
                "text": "{{c1::PFK-1}} is the rate-limiting enzyme of glycolysis.",
                "tags": ["biochemistry"],
            },
            {
                "text": "In glycolysis, PFK-1 converts fructose-6-phosphate to {{c1::fructose-1,6-bisphosphate}}.",
                "tags": ["biochemistry"],
            },
        ]

        cards = await generate_from_chunk(cloze_generator, sample_biochemistry_chunk)

        all_text = " ".join(card.text.lower() for card in cards)
        pathway_terms = ["glycolysis", "pathway", "enzyme", "phosphate"]
        has_pathway = any(term in all_text for term in pathway_terms)
        assert has_pathway, "Biochemistry card should include pathway context"


class TestClozeGeneratorValidation:
    """Tests for cloze generator validation and error handling."""

    @pytest.mark.asyncio
    async def test_filters_invalid_cloze_syntax(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters out cards with invalid cloze syntax."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "This card has no deletions.", "tags": []},  # Invalid
            {"text": "The {{c1::mitochondria}} produces ATP.", "tags": []},  # Valid
            {"text": "Bad syntax {{c1:missing closing}}", "tags": []},  # Invalid
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        # Should only include valid cards
        assert len(cards) == 1
        assert "mitochondria" in cards[0].text

    @pytest.mark.asyncio
    async def test_filters_long_answers(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters out cards with answers exceeding 4 words."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {
                "text": "The {{c1::this answer is way too long for cloze}} is complex.",
                "tags": [],
            },
            {"text": "The {{c1::mitochondria}} produces ATP.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        # Should filter out the card with long answer
        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        for card in cards:
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                assert len(answer.split()) <= 4

    @pytest.mark.asyncio
    async def test_handles_empty_llm_response(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator handles empty LLM response gracefully."""
        mock_llm_client.generate_cloze_cards.return_value = []

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        assert cards == []

    @pytest.mark.asyncio
    async def test_handles_llm_error(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator handles LLM errors gracefully."""
        mock_llm_client.generate_cloze_cards.side_effect = Exception("LLM API error")

        with pytest.raises(Exception) as exc_info:
            await generate_from_chunk(cloze_generator, sample_classified_chunk)

        assert "LLM" in str(exc_info.value) or "error" in str(exc_info.value).lower()


class TestClozeCardUniqueness:
    """Tests for cloze card uniqueness and atomic fact validation."""

    @pytest.mark.asyncio
    async def test_cloze_tests_single_fact(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Each card tests a single atomic fact."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "The {{c1::mitochondria}} is the powerhouse of the cell.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        for card in cards:
            cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
            matches = cloze_pattern.findall(card.text)
            assert len(matches) <= 3, "Card should test a limited number of facts"

    @pytest.mark.asyncio
    async def test_cloze_cards_are_unique(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generated cards have unique content."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "The {{c1::mitochondria}} produces ATP.", "tags": []},
            {"text": "{{c1::ATP}} is the energy currency of the cell.", "tags": []},
            {"text": "The {{c1::Krebs cycle}} generates electron carriers.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        card_texts = [card.text for card in cards]
        assert len(card_texts) == len(set(card_texts)), "All cards should be unique"


class TestAntiTriviaPatterns:
    """Tests for filtering trivia-like content from cloze cards."""

    @pytest.mark.asyncio
    async def test_filters_author_citations(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters cards with author citation deletions."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "According to {{c1::Smith et al.}}, the heart has four chambers.", "tags": []},
            {"text": "{{c1::Johnson (2020)}} showed that aspirin reduces mortality.", "tags": []},
            {"text": "The heart has {{c1::four}} chambers.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        for card in cards:
            assert "et al" not in card.text.lower()
            assert not re.search(r"\{\{c\d+::[A-Z][a-z]+\s+\(\d{4}\)\}\}", card.text)

    @pytest.mark.asyncio
    async def test_filters_figure_references(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters cards with figure/table reference deletions."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "As shown in {{c1::Figure 3}}, glucose is phosphorylated.", "tags": []},
            {"text": "{{c1::Table 2}} lists all drug interactions.", "tags": []},
            {"text": "Glucose is {{c1::phosphorylated}} in the first step.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        for card in cards:
            cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                assert not re.match(r"(?:Figure|Table|Fig\.?)\s*\d+", answer, re.IGNORECASE)

    @pytest.mark.asyncio
    async def test_filters_year_only_deletions(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters cards where the deletion is just a year."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "Penicillin was discovered in {{c1::1928}}.", "tags": []},
            {"text": "The guidelines were updated in {{c1::2019}}.", "tags": []},
            {"text": "Penicillin inhibits {{c1::cell wall}} synthesis.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        for card in cards:
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                assert not re.match(r"^\d{4}$", answer.strip())

    @pytest.mark.asyncio
    async def test_filters_journal_names(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters cards with journal name deletions."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "Published in {{c1::NEJM}}, this study showed benefits.", "tags": []},
            {"text": "The {{c1::Lancet}} published findings on cardiac outcomes.", "tags": []},
            {"text": "Beta-blockers reduce {{c1::mortality}} in heart failure.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        journal_names = {"nejm", "lancet", "jama", "bmj", "nature", "science", "cell"}
        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        for card in cards:
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                assert answer.strip().lower() not in journal_names

    @pytest.mark.asyncio
    async def test_filters_doi_pmid_references(
        self,
        cloze_generator: ClozeGenerator,
        sample_classified_chunk: MockClassifiedChunk,
        mock_llm_client: AsyncMock,
    ) -> None:
        """Generator filters cards with DOI/PMID deletions."""
        mock_llm_client.generate_cloze_cards.return_value = [
            {"text": "Reference: {{c1::PMID 12345678}}.", "tags": []},
            {"text": "DOI: {{c1::10.1000/xyz123}}.", "tags": []},
            {"text": "ACE inhibitors block {{c1::angiotensin converting enzyme}}.", "tags": []},
        ]

        cards = await generate_from_chunk(cloze_generator, sample_classified_chunk)

        cloze_pattern = re.compile(r"\{\{c\d+::([^}]+)\}\}")
        for card in cards:
            answers = cloze_pattern.findall(card.text)
            for answer in answers:
                assert "pmid" not in answer.lower()
                assert not re.match(r"10\.\d+/", answer)
