"""Tests for domain enumerations."""


from tests.conftest import CardType, ContentType, ExamType, ValidationStatus


class TestExamType:
    def test_mcat_value(self):
        assert ExamType.MCAT.value == "mcat"

    def test_usmle_step1_value(self):
        assert ExamType.USMLE_STEP1.value == "usmle_step1"

    def test_all_exam_types_exist(self):
        expected = {"MCAT", "USMLE_STEP1"}
        actual = {e.name for e in ExamType}
        assert actual == expected

    def test_str_representation(self):
        assert str(ExamType.MCAT) == "ExamType.MCAT"
        assert ExamType.MCAT == "mcat"


class TestContentType:
    def test_pdf_textbook_value(self):
        assert ContentType.PDF_TEXTBOOK.value == "pdf_textbook"

    def test_pdf_slides_value(self):
        assert ContentType.PDF_SLIDES.value == "pdf_slides"

    def test_audio_lecture_value(self):
        assert ContentType.AUDIO_LECTURE.value == "audio_lecture"

    def test_markdown_value(self):
        assert ContentType.MARKDOWN.value == "markdown"

    def test_plain_text_value(self):
        assert ContentType.PLAIN_TEXT.value == "plain_text"

    def test_all_content_types_exist(self):
        expected = {"PDF_TEXTBOOK", "PDF_SLIDES", "PDF_NOTES", "AUDIO_LECTURE", "MARKDOWN", "PLAIN_TEXT"}
        actual = {c.name for c in ContentType}
        assert actual == expected


class TestCardType:
    def test_cloze_value(self):
        assert CardType.CLOZE.value == "cloze"

    def test_vignette_value(self):
        assert CardType.VIGNETTE.value == "vignette"

    def test_basic_qa_value(self):
        assert CardType.BASIC_QA.value == "basic_qa"

    def test_all_card_types_exist(self):
        expected = {"CLOZE", "VIGNETTE", "BASIC_QA"}
        actual = {c.name for c in CardType}
        assert actual == expected


class TestValidationStatus:
    def test_valid_status(self):
        assert ValidationStatus.VALID.value == "valid"

    def test_invalid_schema_status(self):
        assert ValidationStatus.INVALID_SCHEMA.value == "invalid_schema"

    def test_invalid_medical_status(self):
        assert ValidationStatus.INVALID_MEDICAL.value == "invalid_medical"

    def test_hallucination_detected_status(self):
        assert ValidationStatus.HALLUCINATION_DETECTED.value == "hallucination_detected"

    def test_duplicate_status(self):
        assert ValidationStatus.DUPLICATE.value == "duplicate"

    def test_all_validation_statuses_exist(self):
        expected = {"VALID", "INVALID_SCHEMA", "INVALID_MEDICAL", "HALLUCINATION_DETECTED", "DUPLICATE"}
        actual = {v.name for v in ValidationStatus}
        assert actual == expected
