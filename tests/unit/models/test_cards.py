"""Tests for ClozeCard validation."""

import pytest

from tests.conftest import ClozeCard


class TestClozeCardValidation:
    def test_valid_cloze_syntax_passes(self):
        """Valid cloze syntax: 'The {{c1::heart}} pumps blood'"""
        card = ClozeCard(
            id="test_001",
            text="The {{c1::heart}} pumps blood",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert is_valid
        assert issues == []

    def test_invalid_cloze_no_deletions_fails(self):
        """Invalid cloze: 'No deletions here'"""
        card = ClozeCard(
            id="test_002",
            text="No deletions here",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert not is_valid
        assert "Missing cloze deletion syntax" in issues

    def test_answer_too_long_fails(self):
        """Invalid cloze: answer exceeds 4 words"""
        card = ClozeCard(
            id="test_003",
            text="The enzyme is {{c1::this answer is way too long for a cloze}}",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert not is_valid
        assert any("too long" in issue for issue in issues)

    def test_multiple_deletions_valid(self):
        """Valid cloze with multiple deletions: '{{c1::A}} and {{c2::B}}'"""
        card = ClozeCard(
            id="test_004",
            text="{{c1::A}} and {{c2::B}} are related concepts",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert is_valid
        assert issues == []

    def test_cloze_with_extra_field(self):
        card = ClozeCard(
            id="test_005",
            text="{{c1::PFK-1}} is the rate-limiting enzyme of glycolysis",
            extra="Allosterically regulated by ATP and citrate",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert is_valid
        assert card.extra == "Allosterically regulated by ATP and citrate"

    def test_cloze_with_tags(self):
        card = ClozeCard(
            id="test_006",
            text="{{c1::Aspirin}} inhibits cyclooxygenase",
            tags=["pharmacology", "cardiovascular"],
            source_chunk_id="chunk_001"
        )
        assert card.tags == ["pharmacology", "cardiovascular"]

    def test_short_answer_passes(self):
        """Answer with 1 word passes"""
        card = ClozeCard(
            id="test_007",
            text="The mitral valve is also called the {{c1::bicuspid}} valve",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert is_valid

    def test_four_word_answer_passes(self):
        """Answer with exactly 4 words passes"""
        card = ClozeCard(
            id="test_008",
            text="The {{c1::left anterior descending artery}} supplies the heart",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert is_valid

    def test_five_word_answer_fails(self):
        """Answer with 5 words fails"""
        card = ClozeCard(
            id="test_009",
            text="The {{c1::left anterior descending coronary artery}} supplies blood",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert not is_valid

    def test_multiple_deletions_one_too_long(self):
        """Multiple deletions where one is too long"""
        card = ClozeCard(
            id="test_010",
            text="{{c1::Metformin}} treats {{c2::type 2 diabetes mellitus condition disorder}}",
            source_chunk_id="chunk_001"
        )
        is_valid, issues = card.validate()
        assert not is_valid

    def test_cloze_pattern_extraction(self):
        """Verify pattern correctly extracts answers"""
        card = ClozeCard(
            id="test_011",
            text="{{c1::Heart}} pumps {{c2::blood}} through {{c3::vessels}}",
            source_chunk_id="chunk_001"
        )
        answers = ClozeCard.CLOZE_PATTERN.findall(card.text)
        assert answers == ["Heart", "blood", "vessels"]

    def test_default_difficulty(self):
        card = ClozeCard(
            id="test_012",
            text="{{c1::Test}} content",
            source_chunk_id="chunk_001"
        )
        assert card.difficulty == "medium"

    def test_custom_difficulty(self):
        card = ClozeCard(
            id="test_013",
            text="{{c1::Complex}} content",
            source_chunk_id="chunk_001",
            difficulty="hard"
        )
        assert card.difficulty == "hard"
