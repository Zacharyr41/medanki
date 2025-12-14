"""Tests for AnKing CrowdAnki export parser."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.ingest.anking_export import AnKingParser, TagNode


@pytest.fixture
def sample_deck_json() -> dict:
    return {
        "name": "AnKing::AnKing Overhaul",
        "notes": [
            {
                "guid": "abc123",
                "tags": [
                    "#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy",
                    "#AK_Step1_v12::#FirstAid::Cardiology::Physiology",
                    "!flag::needsWork",
                ],
                "fields": ["Front", "Back"],
            },
            {
                "guid": "def456",
                "tags": [
                    "#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy",
                    "#AK_Step1_v12::#Pathoma::Cardiac_Path",
                ],
                "fields": ["Front2", "Back2"],
            },
            {
                "guid": "ghi789",
                "tags": [
                    "#AK_Step1_v12::#SketchyMicro::Bacteria::Gram_Positive",
                    "#AK_Step1_v12::#FirstAid::Microbiology",
                ],
                "fields": ["Front3", "Back3"],
            },
            {
                "guid": "jkl012",
                "tags": [],
                "fields": ["Untagged", "Note"],
            },
        ],
    }


@pytest.fixture
def sample_deck_path(sample_deck_json: dict) -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = Path(tmpdir)
        (deck_path / "deck.json").write_text(json.dumps(sample_deck_json))
        yield deck_path


class TestTagNode:
    def test_tag_node_creation(self):
        node = TagNode(name="Cardiology", full_path="#AK_Step1::#B&B::Cardiology")
        assert node.name == "Cardiology"
        assert node.full_path == "#AK_Step1::#B&B::Cardiology"
        assert node.children == {}
        assert node.note_count == 0

    def test_tag_node_with_children(self):
        parent = TagNode(name="B&B", full_path="#AK_Step1::#B&B")
        child = TagNode(name="Cardiology", full_path="#AK_Step1::#B&B::Cardiology")
        parent.children["Cardiology"] = child
        assert "Cardiology" in parent.children
        assert parent.children["Cardiology"].full_path == "#AK_Step1::#B&B::Cardiology"


class TestAnKingParser:
    def test_parser_init(self):
        parser = AnKingParser()
        assert parser.tag_tree == {}
        assert len(parser.tag_counts) == 0

    def test_parse_deck(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        assert len(parser.tag_counts) > 0
        assert "#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy" in parser.tag_counts
        assert parser.tag_counts["#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy"] == 2

    def test_parse_deck_ignores_non_ak_tags(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        assert "!flag::needsWork" not in parser.tag_counts

    def test_parse_deck_builds_tree(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        assert "#AK_Step1_v12" in parser.tag_tree
        step1_node = parser.tag_tree["#AK_Step1_v12"]
        assert "#B&B" in step1_node.children
        assert "#FirstAid" in step1_node.children
        assert "#Pathoma" in step1_node.children
        assert "#SketchyMicro" in step1_node.children

    def test_get_all_tags(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        all_tags = parser.get_all_tags()
        assert len(all_tags) == 5
        assert "#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy" in all_tags

    def test_get_tags_by_resource(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        by_resource = parser.get_tags_by_resource()
        assert "#B&B" in by_resource
        assert "#FirstAid" in by_resource
        assert "#Pathoma" in by_resource
        assert "#SketchyMicro" in by_resource

        assert len(by_resource["#B&B"]) == 1
        assert "#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy" in by_resource["#B&B"]

    def test_get_tag_count(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        assert parser.get_tag_count("#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy") == 2
        assert parser.get_tag_count("#AK_Step1_v12::#FirstAid::Cardiology::Physiology") == 1
        assert parser.get_tag_count("nonexistent") == 0

    def test_export_hierarchy(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        hierarchy = parser.export_hierarchy()
        assert "children" in hierarchy
        assert "#AK_Step1_v12" in hierarchy["children"]

    def test_export_flat_list(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        flat = parser.export_flat_list()
        assert isinstance(flat, list)
        assert len(flat) == 5
        for item in flat:
            assert "tag" in item
            assert "count" in item
            assert "depth" in item

    def test_empty_deck(self):
        parser = AnKingParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            deck_path = Path(tmpdir)
            (deck_path / "deck.json").write_text(json.dumps({"notes": []}))
            parser.parse_deck(deck_path)

        assert len(parser.tag_counts) == 0
        assert parser.tag_tree == {}

    def test_deck_missing_tags(self):
        parser = AnKingParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            deck_path = Path(tmpdir)
            deck_data = {"notes": [{"guid": "abc", "fields": ["F", "B"]}]}
            (deck_path / "deck.json").write_text(json.dumps(deck_data))
            parser.parse_deck(deck_path)

        assert len(parser.tag_counts) == 0

    def test_statistics(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        stats = parser.get_statistics()
        assert stats["total_unique_tags"] == 5
        assert stats["total_tag_assignments"] > 0
        assert "resource_counts" in stats
        assert "#B&B" in stats["resource_counts"]


class TestTagFiltering:
    def test_filter_by_prefix(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        bb_tags = parser.filter_tags(prefix="#AK_Step1_v12::#B&B")
        assert len(bb_tags) == 1
        assert all(t.startswith("#AK_Step1_v12::#B&B") for t in bb_tags)

    def test_filter_by_depth(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        shallow_tags = parser.filter_tags(max_depth=2)
        for tag in shallow_tags:
            assert tag.count("::") <= 2

    def test_filter_by_min_count(self, sample_deck_path: Path):
        parser = AnKingParser()
        parser.parse_deck(sample_deck_path)

        frequent_tags = parser.filter_tags(min_count=2)
        assert "#AK_Step1_v12::#B&B::Cardiology::Heart_Anatomy" in frequent_tags
        for tag in frequent_tags:
            assert parser.tag_counts[tag] >= 2
