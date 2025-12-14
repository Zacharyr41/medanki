from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Any


class IngestionError(Exception):
    pass


@dataclass
class Section:
    title: str
    content: str
    level: int = 1
    page_number: int | None = None


@dataclass
class Document:
    content: str
    source_path: Path
    sections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseExtractor(Protocol):
    def extract(self, path: Path) -> Document: ...


class BaseLoader(Protocol):
    def load(self, path: Path) -> Document: ...
