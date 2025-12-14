"""Chunking service for splitting documents into manageable chunks."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

import tiktoken


class Document(Protocol):
    id: str
    raw_text: str
    sections: list


@dataclass
class Chunk:
    id: str
    document_id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    page_number: Optional[int] = None
    section_path: List[str] = field(default_factory=list)


class TokenCounter:
    def __init__(self, model: str = "gpt-4"):
        self._encoder = tiktoken.encoding_for_model(model)

    def count(self, text: str) -> int:
        return len(self._encoder.encode(text))


class MedicalTermProtector:
    LAB_VALUE_PATTERN = re.compile(
        r"\d+\.?\d*\s*(mg|mcg|g|mL|L|mEq|U|x10\^\d+)/?[A-Za-z]*"
    )
    DRUG_DOSE_PATTERN = re.compile(
        r"[A-Za-z]+\s+\d+\.?\d*\s*(mg|mcg|g|mL)",
        re.IGNORECASE
    )
    ANATOMICAL_PATTERN = re.compile(
        r"(left|right)\s+(anterior|posterior|lateral|medial|main|circumflex|coronary|ventricular|descending)(\s+\w+)?",
        re.IGNORECASE
    )

    def __init__(self):
        self._protected_ranges: List[tuple[int, int]] = []

    def find_protected_ranges(self, text: str) -> List[tuple[int, int]]:
        ranges = []
        for pattern in [self.LAB_VALUE_PATTERN, self.DRUG_DOSE_PATTERN, self.ANATOMICAL_PATTERN]:
            for match in pattern.finditer(text):
                ranges.append((match.start(), match.end()))
        ranges.sort(key=lambda x: x[0])
        return self._merge_overlapping(ranges)

    def _merge_overlapping(self, ranges: List[tuple[int, int]]) -> List[tuple[int, int]]:
        if not ranges:
            return []
        merged = [ranges[0]]
        for start, end in ranges[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    def is_safe_split_point(self, text: str, position: int, protected_ranges: List[tuple[int, int]]) -> bool:
        for start, end in protected_ranges:
            if start < position < end:
                return False
        return True


class SectionAwareChunker:
    def __init__(self, token_counter: TokenCounter):
        self._token_counter = token_counter

    def find_section_boundaries(self, text: str) -> List[int]:
        boundaries = [0]
        header_pattern = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
        for match in header_pattern.finditer(text):
            boundaries.append(match.start())
        return boundaries

    def get_section_path(self, text: str, position: int, sections: list) -> List[str]:
        path = []
        for section in sections:
            if hasattr(section, 'start_char') and hasattr(section, 'end_char'):
                if section.start_char <= position <= section.end_char:
                    path.append(section.title)
        return path


class ChunkingService:
    DEFAULT_CHUNK_SIZE = 512
    DEFAULT_OVERLAP = 75

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP
    ):
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._token_counter = TokenCounter()
        self._term_protector = MedicalTermProtector()
        self._section_chunker = SectionAwareChunker(self._token_counter)

    def chunk(self, document: Document) -> List[Chunk]:
        text = document.raw_text
        if not text or not text.strip():
            return []

        token_count = self._token_counter.count(text)
        if token_count <= self._chunk_size:
            return [self._create_chunk(document, text, 0, len(text))]

        protected_ranges = self._term_protector.find_protected_ranges(text)
        section_boundaries = self._section_chunker.find_section_boundaries(text)
        chunks = []
        start = 0

        while start < len(text):
            target_end = self._find_target_end(text, start)
            if target_end >= len(text):
                target_end = len(text)

            split_point = self._find_best_split_point(
                text, start, target_end, protected_ranges, section_boundaries
            )

            chunk_text = text[start:split_point].strip()
            if chunk_text:
                chunk = self._create_chunk(document, chunk_text, start, split_point)
                chunk.section_path = self._section_chunker.get_section_path(
                    text, start, document.sections
                )
                chunks.append(chunk)

            if split_point >= len(text):
                break

            overlap_start = self._find_overlap_start(text, split_point)
            start = overlap_start

        return chunks

    def _find_target_end(self, text: str, start: int) -> int:
        tokens_counted = 0
        pos = start
        while pos < len(text) and tokens_counted < self._chunk_size:
            next_pos = min(pos + 100, len(text))
            segment = text[pos:next_pos]
            tokens_counted += self._token_counter.count(segment)
            pos = next_pos
        return pos

    def _find_best_split_point(
        self,
        text: str,
        start: int,
        target_end: int,
        protected_ranges: List[tuple[int, int]],
        section_boundaries: List[int]
    ) -> int:
        if target_end >= len(text):
            return len(text)

        search_start = max(start, target_end - 200)
        search_end = min(len(text), target_end + 50)

        for boundary in section_boundaries:
            if search_start < boundary <= search_end:
                if self._term_protector.is_safe_split_point(text, boundary, protected_ranges):
                    return boundary

        sentence_ends = []
        for match in re.finditer(r'[.!?]["\')\]]?\s+', text[search_start:search_end]):
            pos = search_start + match.end()
            if self._term_protector.is_safe_split_point(text, pos, protected_ranges):
                sentence_ends.append(pos)

        if sentence_ends:
            best = min(sentence_ends, key=lambda x: abs(x - target_end))
            return best

        for match in re.finditer(r'\n\n+', text[search_start:search_end]):
            pos = search_start + match.end()
            if self._term_protector.is_safe_split_point(text, pos, protected_ranges):
                return pos

        for match in re.finditer(r'\n', text[search_start:search_end]):
            pos = search_start + match.end()
            if self._term_protector.is_safe_split_point(text, pos, protected_ranges):
                return pos

        return target_end

    def _find_overlap_start(self, text: str, split_point: int) -> int:
        overlap_tokens = 0
        pos = split_point
        while pos > 0 and overlap_tokens < self._overlap:
            prev_pos = max(0, pos - 50)
            segment = text[prev_pos:pos]
            overlap_tokens += self._token_counter.count(segment)
            pos = prev_pos

        sentence_start = text.rfind('. ', pos, split_point)
        if sentence_start != -1:
            return sentence_start + 2

        return pos

    def _create_chunk(
        self,
        document: Document,
        text: str,
        start: int,
        end: int
    ) -> Chunk:
        return Chunk(
            id=f"chunk_{uuid.uuid4().hex[:8]}",
            document_id=document.id,
            text=text,
            start_char=start,
            end_char=end,
            token_count=self._token_counter.count(text),
            section_path=[]
        )
