import re
from pathlib import Path

import pymupdf4llm

from .base import Document, IngestionError, Section


class PDFExtractor:
    def extract(self, path: Path) -> Document:
        md_text = self._extract_with_fallback(path)

        if not md_text:
            raise IngestionError("PDF extraction returned empty result")

        return self._parse_markdown_result(md_text, path)

    def _extract_with_fallback(self, path: Path) -> list | str:
        strategies = [
            {"page_chunks": True},
            {"page_chunks": True, "table_strategy": ""},
            {"page_chunks": False},
            {"page_chunks": False, "table_strategy": ""},
        ]

        last_error = None
        for kwargs in strategies:
            try:
                result = pymupdf4llm.to_markdown(str(path), **kwargs)
                if result:
                    return result
            except Exception as e:
                last_error = e
                continue

        raise IngestionError(f"Failed to extract PDF: {last_error}") from last_error

    def _parse_markdown_result(self, md_text: list | str, path: Path) -> Document:

        full_content = ""
        sections: list[Section] = []
        page_count = len(md_text) if isinstance(md_text, list) else 1

        if isinstance(md_text, list):
            for page_data in md_text:
                page_num = page_data.get("metadata", {}).get("page", 1)
                page_text = page_data.get("text", "")
                full_content += page_text + "\n"

                page_sections = self._extract_sections(page_text, page_num)
                sections.extend(page_sections)
        else:
            full_content = md_text
            sections = self._extract_sections(md_text, 1)

        return Document(
            content=full_content.strip(),
            source_path=path,
            sections=sections,
            metadata={"page_count": page_count},
        )

    def _extract_sections(self, text: str, page_number: int) -> list[Section]:
        sections = []
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        for match in header_pattern.finditer(text):
            level = len(match.group(1))
            title = match.group(2).strip()

            start = match.end()
            next_match = header_pattern.search(text, start)
            end = next_match.start() if next_match else len(text)
            content = text[start:end].strip()

            sections.append(
                Section(
                    title=title,
                    content=content,
                    level=level,
                    page_number=page_number,
                )
            )

        if not sections and text.strip():
            bold_pattern = re.compile(r"\*\*([^*]+)\*\*")
            for match in bold_pattern.finditer(text):
                title = match.group(1).strip()
                if "Chapter" in title or len(title.split()) <= 5:
                    sections.append(
                        Section(
                            title=title,
                            content=text.strip(),
                            level=1,
                            page_number=page_number,
                        )
                    )

        return sections
