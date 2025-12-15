"""Tests for Document and related models."""

from datetime import datetime

from tests.conftest import (
    Chunk,
    ContentType,
    Document,
    MedicalEntity,
    Section,
)


class TestDocument:
    def test_document_creation_with_required_fields(self):
        doc = Document(
            id="doc_001",
            source_path="/path/to/file.pdf",
            content_type=ContentType.PDF_TEXTBOOK,
            raw_text="Medical content here",
        )
        assert doc.id == "doc_001"
        assert doc.source_path == "/path/to/file.pdf"
        assert doc.content_type == ContentType.PDF_TEXTBOOK
        assert doc.raw_text == "Medical content here"

    def test_document_default_sections(self):
        doc = Document(
            id="doc_001",
            source_path="/path/to/file.pdf",
            content_type=ContentType.PDF_TEXTBOOK,
            raw_text="Content",
        )
        assert doc.sections == []

    def test_document_default_metadata(self):
        doc = Document(
            id="doc_001",
            source_path="/path/to/file.pdf",
            content_type=ContentType.PDF_TEXTBOOK,
            raw_text="Content",
        )
        assert doc.metadata == {}

    def test_document_extracted_at_default(self):
        before = datetime.utcnow()
        doc = Document(
            id="doc_001",
            source_path="/path/to/file.pdf",
            content_type=ContentType.PDF_TEXTBOOK,
            raw_text="Content",
        )
        after = datetime.utcnow()
        assert before <= doc.extracted_at <= after

    def test_document_with_sections(self, sample_document):
        assert len(sample_document.sections) == 1
        assert sample_document.sections[0].title == "Introduction"

    def test_document_with_metadata(self, sample_document):
        assert sample_document.metadata.get("page_count") == 10


class TestSection:
    def test_section_creation(self):
        section = Section(title="Chapter 1: Introduction", level=1, start_char=0, end_char=500)
        assert section.title == "Chapter 1: Introduction"
        assert section.level == 1
        assert section.start_char == 0
        assert section.end_char == 500
        assert section.page_number is None

    def test_section_with_page_number(self):
        section = Section(title="Subsection", level=2, start_char=100, end_char=200, page_number=5)
        assert section.page_number == 5

    def test_section_levels(self):
        chapter = Section(title="Chapter", level=1, start_char=0, end_char=100)
        section = Section(title="Section", level=2, start_char=0, end_char=50)
        subsection = Section(title="Subsection", level=3, start_char=0, end_char=25)
        assert chapter.level == 1
        assert section.level == 2
        assert subsection.level == 3


class TestChunk:
    def test_chunk_creation_with_required_fields(self):
        chunk = Chunk(
            id="chunk_001",
            document_id="doc_001",
            text="The cardiac cycle consists of systole and diastole.",
            start_char=0,
            end_char=51,
            token_count=10,
        )
        assert chunk.id == "chunk_001"
        assert chunk.document_id == "doc_001"
        assert chunk.text == "The cardiac cycle consists of systole and diastole."
        assert chunk.start_char == 0
        assert chunk.end_char == 51
        assert chunk.token_count == 10

    def test_chunk_default_entities(self):
        chunk = Chunk(
            id="chunk_001",
            document_id="doc_001",
            text="Sample text",
            start_char=0,
            end_char=11,
            token_count=2,
        )
        assert chunk.entities == []

    def test_chunk_default_embedding(self):
        chunk = Chunk(
            id="chunk_001",
            document_id="doc_001",
            text="Sample text",
            start_char=0,
            end_char=11,
            token_count=2,
        )
        assert chunk.embedding is None

    def test_chunk_text_property(self):
        chunk = Chunk(
            id="chunk_001",
            document_id="doc_001",
            text="Medical content here",
            start_char=100,
            end_char=120,
            token_count=3,
        )
        assert chunk.text == "Medical content here"
        assert len(chunk.text) == 20

    def test_chunk_with_entities(self):
        entity = MedicalEntity(text="metformin", label="DRUG", start=0, end=9)
        chunk = Chunk(
            id="chunk_001",
            document_id="doc_001",
            text="metformin is used to treat diabetes",
            start_char=0,
            end_char=35,
            token_count=6,
            entities=[entity],
        )
        assert len(chunk.entities) == 1
        assert chunk.entities[0].text == "metformin"
        assert chunk.entities[0].label == "DRUG"

    def test_chunk_token_count(self):
        chunk = Chunk(
            id="chunk_001",
            document_id="doc_001",
            text="This is a sample chunk with several tokens for testing.",
            start_char=0,
            end_char=56,
            token_count=10,
        )
        assert chunk.token_count == 10


class TestMedicalEntity:
    def test_medical_entity_creation(self):
        entity = MedicalEntity(text="congestive heart failure", label="DISEASE", start=10, end=34)
        assert entity.text == "congestive heart failure"
        assert entity.label == "DISEASE"
        assert entity.start == 10
        assert entity.end == 34

    def test_medical_entity_with_umls_cui(self):
        entity = MedicalEntity(text="metformin", label="DRUG", start=0, end=9, cui="C0025598")
        assert entity.cui == "C0025598"

    def test_medical_entity_default_cui(self):
        entity = MedicalEntity(text="hypertension", label="DISEASE", start=0, end=12)
        assert entity.cui is None

    def test_medical_entity_default_confidence(self):
        entity = MedicalEntity(text="aspirin", label="DRUG", start=0, end=7)
        assert entity.confidence == 1.0

    def test_medical_entity_custom_confidence(self):
        entity = MedicalEntity(
            text="possible cardiomyopathy", label="DISEASE", start=0, end=23, confidence=0.75
        )
        assert entity.confidence == 0.75

    def test_valid_entity_labels(self):
        valid_labels = ["DISEASE", "DRUG", "ANATOMY", "PROCEDURE", "GENE", "SYMPTOM"]
        for label in valid_labels:
            entity = MedicalEntity(text="test", label=label, start=0, end=4)
            assert entity.label == label
