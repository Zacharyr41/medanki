"""Unit tests for anti-trivia rules in cloze generation."""

import re

TRIVIA_PATTERNS = {
    "study_name": re.compile(r"\b[A-Z]{2,}(?:-[A-Z]+)*\s+(?:trial|study|cohort)\b", re.IGNORECASE),
    "hazard_ratio": re.compile(r"\bHR\s*[=:]\s*\d+\.?\d*"),
    "p_value": re.compile(r"\bp\s*[<>=]\s*0?\.\d+"),
    "year_guideline": re.compile(r"\b(?:19|20)\d{2}\s+(?:guidelines?|recommendations?)\b", re.IGNORECASE),
    "confidence_interval": re.compile(r"\b\d+%?\s*CI\b|\bconfidence interval\b", re.IGNORECASE),
    "relative_risk": re.compile(r"\bRR\s*[=:]\s*\d+\.?\d*"),
    "odds_ratio": re.compile(r"\bOR\s*[=:]\s*\d+\.?\d*"),
    "specific_percentage": re.compile(r"\b\d{1,2}(?:\.\d+)?%"),
}

CLOZE_PATTERN = re.compile(r"\{\{c\d+::([^}]+)\}\}")


def extract_cloze_answers(text: str) -> list[str]:
    """Extract all cloze deletion answers from text."""
    return [match.group(1) for match in CLOZE_PATTERN.finditer(text)]


def contains_trivia(text: str) -> bool:
    """Check if text contains research trivia patterns."""
    return any(pattern.search(text) for pattern in TRIVIA_PATTERNS.values())


def has_trivia_deletion(card_text: str) -> bool:
    """Check if any cloze deletion contains trivia."""
    answers = extract_cloze_answers(card_text)
    return any(contains_trivia(answer) for answer in answers)


class TestTriviaDetection:
    """Tests for trivia pattern detection."""

    def test_detects_study_name(self):
        """Should detect study/trial names."""
        assert contains_trivia("The ASCOT trial showed benefits")
        assert contains_trivia("HOPE study demonstrated")
        assert contains_trivia("MESA cohort findings")

    def test_detects_hazard_ratio(self):
        """Should detect hazard ratios."""
        assert contains_trivia("HR = 0.85")
        assert contains_trivia("HR: 1.23")
        assert contains_trivia("with HR=0.7")

    def test_detects_p_value(self):
        """Should detect p-values."""
        assert contains_trivia("p < 0.05")
        assert contains_trivia("p = 0.001")
        assert contains_trivia("p<.01")

    def test_detects_guideline_years(self):
        """Should detect guideline years."""
        assert contains_trivia("2019 guidelines recommend")
        assert contains_trivia("per 2022 recommendations")

    def test_detects_confidence_intervals(self):
        """Should detect confidence intervals."""
        assert contains_trivia("95% CI")
        assert contains_trivia("confidence interval")

    def test_detects_relative_risk(self):
        """Should detect relative risk."""
        assert contains_trivia("RR = 1.5")
        assert contains_trivia("RR: 0.8")

    def test_detects_odds_ratio(self):
        """Should detect odds ratios."""
        assert contains_trivia("OR = 2.3")
        assert contains_trivia("OR: 0.6")

    def test_does_not_flag_mechanisms(self):
        """Should not flag mechanistic content."""
        assert not contains_trivia("inhibits HMG-CoA reductase")
        assert not contains_trivia("activates adenylyl cyclase")
        assert not contains_trivia("causes endothelial dysfunction")

    def test_does_not_flag_pathophysiology(self):
        """Should not flag pathophysiology concepts."""
        assert not contains_trivia("atherosclerotic plaque formation")
        assert not contains_trivia("intima-media thickening")
        assert not contains_trivia("inflammatory cascade")


class TestClozeTriviaFiltering:
    """Tests for filtering trivia from cloze deletions."""

    def test_good_mechanism_cloze(self):
        """Good cards should test mechanisms."""
        good_cards = [
            "Statins inhibit {{c1::HMG-CoA reductase}}, reducing cholesterol synthesis.",
            "Atherosclerosis begins with {{c1::endothelial dysfunction}}.",
            "{{c1::Metformin}} decreases hepatic glucose production.",
            "The {{c1::LAD}} artery supplies the anterior left ventricle.",
        ]
        for card in good_cards:
            assert not has_trivia_deletion(card), f"Good card flagged as trivia: {card}"

    def test_bad_study_cloze(self):
        """Bad cards should not test study names."""
        bad_cards = [
            "The {{c1::ASCOT trial}} showed statins reduce events.",
            "{{c1::MESA study}} demonstrated cIMT correlation.",
        ]
        for card in bad_cards:
            assert has_trivia_deletion(card), f"Trivia card not detected: {card}"

    def test_bad_statistics_cloze(self):
        """Bad cards should not test specific statistics."""
        bad_cards = [
            "Statins reduced events with {{c1::HR = 0.85}}.",
            "The effect was significant ({{c1::p < 0.001}}).",
            "Risk decreased by {{c1::23%}} with treatment.",
        ]
        for card in bad_cards:
            assert has_trivia_deletion(card), f"Trivia card not detected: {card}"

    def test_bad_guideline_year_cloze(self):
        """Bad cards should not test guideline years."""
        bad_cards = [
            "Per {{c1::2019 guidelines}}, statins are recommended.",
            "{{c1::2022 recommendations}} suggest early intervention.",
        ]
        for card in bad_cards:
            assert has_trivia_deletion(card), f"Trivia card not detected: {card}"


class TestClozeExtraction:
    """Tests for cloze answer extraction."""

    def test_extracts_single_cloze(self):
        """Should extract single cloze answer."""
        text = "{{c1::Metformin}} is a biguanide."
        answers = extract_cloze_answers(text)
        assert answers == ["Metformin"]

    def test_extracts_multiple_cloze(self):
        """Should extract multiple cloze answers."""
        text = "{{c1::ATP}} is produced via {{c2::oxidative phosphorylation}}."
        answers = extract_cloze_answers(text)
        assert answers == ["ATP", "oxidative phosphorylation"]

    def test_handles_no_cloze(self):
        """Should return empty list for no cloze."""
        text = "This is a regular sentence."
        answers = extract_cloze_answers(text)
        assert answers == []
