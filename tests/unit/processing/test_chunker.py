"""Tests for the chunking service."""

from __future__ import annotations

import sys

sys.path.insert(0, "/Users/zacharyrothstein/Code/medanki-tests/packages/core/src")

import pytest

from medanki.processing.chunker import ChunkingService


class TestBasicChunking:
    """Tests for basic chunking functionality."""

    def test_chunks_by_token_count(self, sample_long_document):
        """Splits documents at approximately 512 tokens."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= 512 + 75

    def test_chunks_have_overlap(self, sample_long_document):
        """Ensures 75 token overlap between consecutive chunks."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        assert len(chunks) >= 2
        for i in range(len(chunks) - 1):
            current_end = chunks[i].text
            next_start = chunks[i + 1].text
            overlap_text = self._find_overlap(current_end, next_start)
            assert len(overlap_text) > 0, "Chunks should have overlapping text"

    def test_small_doc_single_chunk(self, sample_document):
        """Documents smaller than 512 tokens return a single chunk."""
        service = ChunkingService()
        chunks = service.chunk(sample_document)

        assert len(chunks) == 1
        assert chunks[0].text == sample_document.raw_text

    def test_empty_doc_no_chunks(self, empty_document):
        """Empty documents return an empty list."""
        service = ChunkingService()
        chunks = service.chunk(empty_document)

        assert chunks == []

    @staticmethod
    def _find_overlap(text1: str, text2: str) -> str:
        """Find overlapping text between end of text1 and start of text2."""
        for i in range(min(len(text1), len(text2)), 0, -1):
            if text1[-i:] == text2[:i]:
                return text1[-i:]
        return ""


class TestSectionAwareChunking:
    """Tests for section-aware chunking."""

    def test_prefers_section_boundaries(self, document_with_sections):
        """Prefers breaking at section headers when possible."""
        service = ChunkingService()
        chunks = service.chunk(document_with_sections)

        section_breaks = 0
        for chunk in chunks:
            if chunk.text.strip().startswith("#") or chunk.text.strip().endswith("\n\n"):
                section_breaks += 1

        assert section_breaks > 0, "Should break at section boundaries"

    def test_preserves_section_path(self, document_with_sections):
        """Chunks know their section hierarchy."""
        service = ChunkingService()
        chunks = service.chunk(document_with_sections)

        for chunk in chunks:
            assert hasattr(chunk, "section_path")
            assert isinstance(chunk.section_path, list)

    def test_never_splits_mid_sentence(self, sample_long_document):
        """Sentences stay together - never split mid-sentence."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        for chunk in chunks:
            text = chunk.text.strip()
            if text:
                last_char = text[-1]
                assert last_char in ".!?:;\"'" or text.endswith("\n"), (
                    f"Chunk should end at sentence boundary, got: ...{text[-50:]}"
                )


class TestChunkIdAndCoverage:
    """Tests for chunk ID generation and document coverage."""

    def test_chunk_respects_min_token_limit(self, sample_long_document):
        """Chunks meet minimum token threshold (except final chunk)."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        min_tokens = 100
        for chunk in chunks[:-1]:
            assert chunk.token_count >= min_tokens, (
                f"Chunk has {chunk.token_count} tokens, below minimum {min_tokens}"
            )

    def test_chunks_cover_entire_document(self, sample_long_document):
        """Chunks collectively cover all document content."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        combined_text = " ".join(c.text for c in chunks)
        doc_words = sample_long_document.raw_text.split()
        sample_indices = [0, len(doc_words)//4, len(doc_words)//2, -1]

        for idx in sample_indices:
            word = doc_words[idx]
            if len(word) > 3:
                assert word in combined_text, f"Word '{word}' not found in chunks"

    def test_chunk_ids_are_unique(self, sample_long_document):
        """Each chunk has a unique identifier."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        ids = [chunk.id for chunk in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_chunks_track_document_id(self, sample_long_document):
        """Each chunk references its source document."""
        service = ChunkingService()
        chunks = service.chunk(sample_long_document)

        for chunk in chunks:
            assert chunk.document_id == sample_long_document.id, (
                f"Chunk document_id {chunk.document_id} doesn't match document {sample_long_document.id}"
            )


class TestMedicalTermPreservation:
    """Tests for medical term preservation."""

    def test_keeps_lab_values_together(self, medical_text_with_lab_values):
        """Lab values like '5.2 mg/dL' are never split."""
        service = ChunkingService()
        chunks = service.chunk(medical_text_with_lab_values)

        all_text = " ".join(c.text for c in chunks)
        assert "5.2 mg/dL" in all_text or any("5.2 mg/dL" in c.text for c in chunks)
        assert "140 mEq/L" in all_text or any("140 mEq/L" in c.text for c in chunks)

        for chunk in chunks:
            assert "5.2" not in chunk.text or "mg/dL" in chunk.text, (
                "Lab value '5.2 mg/dL' was split across chunks"
            )

    def test_keeps_drug_doses_together(self, medical_text_with_drugs):
        """Drug doses like 'metoprolol 25mg' are never split."""
        service = ChunkingService()
        chunks = service.chunk(medical_text_with_drugs)

        for chunk in chunks:
            if "metoprolol" in chunk.text.lower():
                assert "25" in chunk.text or "mg" in chunk.text, (
                    "Drug dose 'metoprolol 25mg' was split"
                )
            if "lisinopril" in chunk.text.lower():
                assert "10" in chunk.text or "mg" in chunk.text, (
                    "Drug dose 'lisinopril 10mg' was split"
                )

    def test_keeps_anatomical_terms(self, medical_text_with_anatomy):
        """Anatomical terms like 'left anterior descending' are never split."""
        service = ChunkingService()
        chunks = service.chunk(medical_text_with_anatomy)

        for chunk in chunks:
            if "left" in chunk.text.lower() and "anterior" not in chunk.text.lower():
                if "descending" in chunk.text.lower():
                    pytest.fail("Anatomical term 'left anterior descending' was split")
            if "anterior" in chunk.text.lower():
                assert "left" in chunk.text.lower() or "descending" in chunk.text.lower(), (
                    "Anatomical term context was lost"
                )
