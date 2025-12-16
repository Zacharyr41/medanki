"""Tests for ClozeCard validation."""

from tests.conftest import ClozeCard, VignetteCard


class TestClozeCardValidation:
    def test_valid_cloze_syntax_passes(self):
        """Valid cloze syntax: 'The {{c1::heart}} pumps blood'"""
        card = ClozeCard(
            id="test_001", text="The {{c1::heart}} pumps blood", source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert is_valid
        assert issues == []

    def test_invalid_cloze_no_deletions_fails(self):
        """Invalid cloze: 'No deletions here'"""
        card = ClozeCard(id="test_002", text="No deletions here", source_chunk_id="chunk_001")
        is_valid, issues = card.validate()
        assert not is_valid
        assert "Missing cloze deletion syntax" in issues

    def test_answer_too_long_fails(self):
        """Invalid cloze: answer exceeds 4 words"""
        card = ClozeCard(
            id="test_003",
            text="The enzyme is {{c1::this answer is way too long for a cloze}}",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert not is_valid
        assert any("too long" in issue for issue in issues)

    def test_multiple_deletions_valid(self):
        """Valid cloze with multiple deletions: '{{c1::A}} and {{c2::B}}'"""
        card = ClozeCard(
            id="test_004",
            text="{{c1::A}} and {{c2::B}} are related concepts",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert is_valid
        assert issues == []

    def test_cloze_with_extra_field(self):
        card = ClozeCard(
            id="test_005",
            text="{{c1::PFK-1}} is the rate-limiting enzyme of glycolysis",
            extra="Allosterically regulated by ATP and citrate",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert is_valid
        assert card.extra == "Allosterically regulated by ATP and citrate"

    def test_cloze_with_tags(self):
        card = ClozeCard(
            id="test_006",
            text="{{c1::Aspirin}} inhibits cyclooxygenase",
            tags=["pharmacology", "cardiovascular"],
            source_chunk_id="chunk_001",
        )
        assert card.tags == ["pharmacology", "cardiovascular"]

    def test_short_answer_passes(self):
        """Answer with 1 word passes"""
        card = ClozeCard(
            id="test_007",
            text="The mitral valve is also called the {{c1::bicuspid}} valve",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert is_valid

    def test_four_word_answer_passes(self):
        """Answer with exactly 4 words passes"""
        card = ClozeCard(
            id="test_008",
            text="The {{c1::left anterior descending artery}} supplies the heart",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert is_valid

    def test_five_word_answer_fails(self):
        """Answer with 5 words fails"""
        card = ClozeCard(
            id="test_009",
            text="The {{c1::left anterior descending coronary artery}} supplies blood",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert not is_valid

    def test_multiple_deletions_one_too_long(self):
        """Multiple deletions where one is too long"""
        card = ClozeCard(
            id="test_010",
            text="{{c1::Metformin}} treats {{c2::type 2 diabetes mellitus condition disorder}}",
            source_chunk_id="chunk_001",
        )
        is_valid, issues = card.validate()
        assert not is_valid

    def test_cloze_pattern_extraction(self):
        """Verify pattern correctly extracts answers"""
        card = ClozeCard(
            id="test_011",
            text="{{c1::Heart}} pumps {{c2::blood}} through {{c3::vessels}}",
            source_chunk_id="chunk_001",
        )
        answers = ClozeCard.CLOZE_PATTERN.findall(card.text)
        assert answers == ["Heart", "blood", "vessels"]

    def test_default_difficulty(self):
        card = ClozeCard(id="test_012", text="{{c1::Test}} content", source_chunk_id="chunk_001")
        assert card.difficulty == "medium"

    def test_custom_difficulty(self):
        card = ClozeCard(
            id="test_013",
            text="{{c1::Complex}} content",
            source_chunk_id="chunk_001",
            difficulty="hard",
        )
        assert card.difficulty == "hard"


class TestDocumentPosition:
    """Tests for document_position field on cards."""

    def test_cloze_card_default_position(self):
        """ClozeCard has default document_position of 0."""
        card = ClozeCard(
            id="test_pos_001",
            text="{{c1::Test}} content",
            source_chunk_id="chunk_001",
        )
        assert card.document_position == 0

    def test_cloze_card_custom_position(self):
        """ClozeCard accepts custom document_position."""
        card = ClozeCard(
            id="test_pos_002",
            text="{{c1::Test}} content",
            source_chunk_id="chunk_001",
            document_position=1500,
        )
        assert card.document_position == 1500

    def test_vignette_card_default_position(self):
        """VignetteCard has default document_position of 0."""
        card = VignetteCard(
            id="vignette_pos_001",
            front="What is the diagnosis?",
            answer="Test answer",
            explanation="Test explanation",
            source_chunk_id="chunk_001",
        )
        assert card.document_position == 0

    def test_vignette_card_custom_position(self):
        """VignetteCard accepts custom document_position."""
        card = VignetteCard(
            id="vignette_pos_002",
            front="What is the diagnosis?",
            answer="Test answer",
            explanation="Test explanation",
            source_chunk_id="chunk_001",
            document_position=3200,
        )
        assert card.document_position == 3200

    def test_cards_sortable_by_position(self):
        """Cards can be sorted by document_position."""
        cards = [
            ClozeCard(
                id="c1",
                text="{{c1::Third}} item",
                source_chunk_id="chunk_003",
                document_position=3000,
            ),
            ClozeCard(
                id="c2",
                text="{{c1::First}} item",
                source_chunk_id="chunk_001",
                document_position=500,
            ),
            ClozeCard(
                id="c3",
                text="{{c1::Second}} item",
                source_chunk_id="chunk_002",
                document_position=1500,
            ),
        ]
        sorted_cards = sorted(cards, key=lambda c: c.document_position)
        assert sorted_cards[0].id == "c2"
        assert sorted_cards[1].id == "c3"
        assert sorted_cards[2].id == "c1"


class TestVignetteCard:
    def test_vignette_creation(self):
        card = VignetteCard(
            id="vignette_001",
            front="A 45-year-old male presents with chest pain. What is the most likely diagnosis?",
            answer="Myocardial infarction",
            explanation="The presentation is classic for MI with chest pain radiating to arm.",
            source_chunk_id="chunk_001",
        )
        assert card.id == "vignette_001"
        assert card.answer == "Myocardial infarction"

    def test_vignette_with_demographics(self):
        card = VignetteCard(
            id="vignette_002",
            front="A 65-year-old female with a history of diabetes presents with fatigue.",
            answer="Diabetic ketoacidosis",
            explanation="Classic presentation in diabetic patient.",
            source_chunk_id="chunk_001",
        )
        assert "65-year-old" in card.front
        assert "female" in card.front

    def test_vignette_ends_with_question(self):
        card = VignetteCard(
            id="vignette_003",
            front="A patient presents with symptoms. What is the diagnosis?",
            answer="Test answer",
            explanation="Test explanation",
            source_chunk_id="chunk_001",
        )
        assert card.front.endswith("?")

    def test_vignette_concise_answer(self):
        card = VignetteCard(
            id="vignette_004",
            front="What is the diagnosis?",
            answer="Heart failure",
            explanation="Signs and symptoms point to CHF.",
            source_chunk_id="chunk_001",
        )
        word_count = len(card.answer.split())
        assert word_count <= 3

    def test_vignette_has_explanation(self):
        card = VignetteCard(
            id="vignette_005",
            front="Clinical stem here?",
            answer="Answer",
            explanation="Detailed explanation of the diagnosis and reasoning.",
            source_chunk_id="chunk_001",
        )
        assert len(card.explanation) > 0
        assert card.explanation == "Detailed explanation of the diagnosis and reasoning."

    def test_vignette_with_distinguishing_feature(self):
        card = VignetteCard(
            id="vignette_006",
            front="A patient presents with a rash. What is the diagnosis?",
            answer="Erythema migrans",
            explanation="Classic target lesion of Lyme disease.",
            distinguishing_feature="Target-shaped rash with central clearing",
            source_chunk_id="chunk_001",
        )
        assert card.distinguishing_feature == "Target-shaped rash with central clearing"

    def test_vignette_with_tags(self):
        card = VignetteCard(
            id="vignette_007",
            front="Clinical vignette here?",
            answer="Diagnosis",
            explanation="Explanation here.",
            tags=["cardiology", "USMLE::Step1"],
            source_chunk_id="chunk_001",
        )
        assert card.tags == ["cardiology", "USMLE::Step1"]
        assert len(card.tags) == 2
