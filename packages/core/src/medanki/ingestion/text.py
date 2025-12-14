import re
from pathlib import Path

from .base import Document, Section


class TextLoader:
    def load(self, path: Path) -> Document:
        content = path.read_text(encoding="utf-8")

        return Document(
            content=content,
            source_path=path,
            sections=[],
            metadata={"format": "plain_text"},
        )


class MarkdownLoader:
    def load(self, path: Path) -> Document:
        content = path.read_text(encoding="utf-8")

        if not content.strip():
            return Document(
                content="",
                source_path=path,
                sections=[],
                metadata={"format": "markdown"},
            )

        sections = self._extract_sections(content)

        return Document(
            content=content,
            source_path=path,
            sections=sections,
            metadata={"format": "markdown"},
        )

    def _extract_sections(self, text: str) -> list[Section]:
        sections = []
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        matches = list(header_pattern.finditer(text))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()

            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            sections.append(
                Section(
                    title=title,
                    content=content,
                    level=level,
                    page_number=None,
                )
            )

        return sections
