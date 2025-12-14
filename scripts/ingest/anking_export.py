#!/usr/bin/env python3
"""Parse AnKing CrowdAnki exports to extract tag hierarchy."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(help="AnKing deck parser utilities")

TAG_PREFIXES = {
    "#AK_Step1_v12::#B&B": "Boards & Beyond",
    "#AK_Step1_v12::#FirstAid": "First Aid",
    "#AK_Step1_v12::#Pathoma": "Pathoma",
    "#AK_Step1_v12::#SketchyMicro": "Sketchy Micro",
    "#AK_Step1_v12::#SketchyPharm": "Sketchy Pharm",
    "#AK_Step1_v12::#SketchyPath": "Sketchy Path",
    "#AK_Step1_v12::#Costanzo": "Costanzo",
    "#AK_Step1_v12::#UWorld": "UWorld",
}


@dataclass
class TagNode:
    name: str
    full_path: str
    children: dict[str, TagNode] = field(default_factory=dict)
    note_count: int = 0


class AnKingParser:
    def __init__(self) -> None:
        self.tag_tree: dict[str, TagNode] = {}
        self.tag_counts: dict[str, int] = defaultdict(int)

    def parse_deck(self, deck_path: Path) -> None:
        deck_file = deck_path / "deck.json"
        deck = json.loads(deck_file.read_text())

        for note in deck.get("notes", []):
            for tag in note.get("tags", []):
                if tag.startswith("#AK_"):
                    self._add_tag(tag)

    def _add_tag(self, tag: str) -> None:
        self.tag_counts[tag] += 1

        parts = tag.split("::")
        current_level = self.tag_tree

        for i, part in enumerate(parts):
            path = "::".join(parts[: i + 1])
            if part not in current_level:
                current_level[part] = TagNode(name=part, full_path=path)
            current_level[part].note_count += 1
            current_level = current_level[part].children

    def get_all_tags(self) -> set[str]:
        return set(self.tag_counts.keys())

    def get_tags_by_resource(self) -> dict[str, set[str]]:
        by_resource: dict[str, set[str]] = defaultdict(set)

        for tag in self.tag_counts:
            parts = tag.split("::")
            if len(parts) >= 2:
                resource = parts[1]
                by_resource[resource].add(tag)

        return dict(by_resource)

    def get_tag_count(self, tag: str) -> int:
        return self.tag_counts.get(tag, 0)

    def export_hierarchy(self) -> dict[str, Any]:
        def node_to_dict(node: TagNode) -> dict[str, Any]:
            return {
                "name": node.name,
                "full_path": node.full_path,
                "note_count": node.note_count,
                "children": {
                    name: node_to_dict(child) for name, child in node.children.items()
                },
            }

        return {
            "children": {
                name: node_to_dict(node) for name, node in self.tag_tree.items()
            }
        }

    def export_flat_list(self) -> list[dict[str, Any]]:
        result = []
        for tag, count in self.tag_counts.items():
            depth = tag.count("::")
            result.append({"tag": tag, "count": count, "depth": depth})
        return sorted(result, key=lambda x: x["tag"])

    def get_statistics(self) -> dict[str, Any]:
        by_resource = self.get_tags_by_resource()
        resource_counts = {res: len(tags) for res, tags in by_resource.items()}

        return {
            "total_unique_tags": len(self.tag_counts),
            "total_tag_assignments": sum(self.tag_counts.values()),
            "resource_counts": resource_counts,
        }

    def filter_tags(
        self,
        prefix: str | None = None,
        max_depth: int | None = None,
        min_count: int | None = None,
    ) -> set[str]:
        result = set()

        for tag, count in self.tag_counts.items():
            if prefix and not tag.startswith(prefix):
                continue
            if max_depth is not None and tag.count("::") > max_depth:
                continue
            if min_count is not None and count < min_count:
                continue
            result.add(tag)

        return result


@app.command()
def extract_tags(
    deck_path: Path = typer.Argument(
        Path("data/source/anking/AnKing-v11"),
        help="Path to the AnKing deck directory",
    ),
    output: Path = typer.Option(
        Path("data/anking_tags.json"),
        help="Output JSON file path",
    ),
    format: str = typer.Option(
        "hierarchy",
        help="Output format: hierarchy, flat, or stats",
    ),
) -> None:
    """Extract tags from an AnKing deck export."""
    parser = AnKingParser()
    parser.parse_deck(deck_path)

    stats = parser.get_statistics()
    typer.echo(f"Found {stats['total_unique_tags']} unique tags")
    typer.echo(f"Total tag assignments: {stats['total_tag_assignments']}")

    data: dict[str, Any] | list[dict[str, Any]]
    if format == "hierarchy":
        data = parser.export_hierarchy()
    elif format == "flat":
        data = parser.export_flat_list()
    elif format == "stats":
        data = stats
    else:
        typer.echo(f"Unknown format: {format}", err=True)
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2))
    typer.echo(f"Saved to {output}")


@app.command()
def list_resources(
    deck_path: Path = typer.Argument(
        Path("data/source/anking/AnKing-v11"),
        help="Path to the AnKing deck directory",
    ),
) -> None:
    """List all resource types found in the deck."""
    parser = AnKingParser()
    parser.parse_deck(deck_path)

    by_resource = parser.get_tags_by_resource()
    for resource, tags in sorted(by_resource.items()):
        display_name = TAG_PREFIXES.get(f"#AK_Step1_v12::{resource}", resource)
        typer.echo(f"{display_name}: {len(tags)} tags")


if __name__ == "__main__":
    app()
