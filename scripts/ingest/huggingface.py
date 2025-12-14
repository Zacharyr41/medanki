#!/usr/bin/env python3
"""
Ingest medical Q&A datasets from Hugging Face.

Usage:
    python scripts/ingest/huggingface.py extract-topics
    python scripts/ingest/huggingface.py download-all
    python scripts/ingest/huggingface.py enrich-taxonomy
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
from datasets import load_dataset

app = typer.Typer(help="Hugging Face dataset ingestion for MedAnki")

REQUIRED_MEDMCQA_FIELDS = {"subject_name", "topic_name", "question"}

SUBJECT_TO_TAXONOMY = {
    "Anatomy": "organ_systems",
    "Physiology": "organ_systems",
    "Biochemistry": "biochemistry_metabolism",
    "Pharmacology": "pharmacology",
    "Pathology": "pathology",
    "Microbiology": "microbiology",
    "Forensic Medicine": "other",
    "Psychiatry": "behavioral_sciences",
    "Medicine": "organ_systems",
    "Pediatrics": "organ_systems",
    "Surgery": "organ_systems",
    "Gynaecology & Obstetrics": "organ_systems",
    "Ophthalmology": "organ_systems",
    "ENT": "organ_systems",
    "Orthopaedics": "organ_systems",
    "Radiology": "other",
    "Skin": "organ_systems",
    "Anaesthesia": "pharmacology",
    "Dental": "other",
    "Social & Preventive Medicine": "population_health",
    "Unknown": "other",
}


@dataclass
class DatasetConfig:
    """Configuration for a Hugging Face dataset."""

    name: str
    repo: str
    description: str
    splits: list[str] = field(default_factory=lambda: ["train"])


@dataclass
class TopicStats:
    """Tracks topic statistics across subjects."""

    _subjects: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    _totals: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_topic(self, subject: str, topic: str) -> None:
        self._subjects[subject][topic] += 1
        self._totals[subject] += 1

    def get_subject_count(self, subject: str) -> int:
        return self._totals.get(subject, 0)

    def get_unique_topics(self, subject: str) -> int:
        return len(self._subjects.get(subject, {}))

    def get_topic_count(self, subject: str, topic: str) -> int:
        return self._subjects.get(subject, {}).get(topic, 0)

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for subject, topics in self._subjects.items():
            sorted_topics = dict(sorted(topics.items(), key=lambda x: -x[1]))
            result[subject] = {
                "total_questions": self._totals[subject],
                "unique_topics": len(topics),
                "topics": sorted_topics,
            }
        return result

    def get_summary(self) -> dict[str, int]:
        total_questions = sum(self._totals.values())
        total_subjects = len(self._subjects)
        total_unique_topics = sum(len(topics) for topics in self._subjects.values())
        return {
            "total_questions": total_questions,
            "total_subjects": total_subjects,
            "total_unique_topics": total_unique_topics,
        }


def get_dataset_configs() -> list[DatasetConfig]:
    """Return all configured datasets for ingestion."""
    return [
        DatasetConfig(
            name="medmcqa",
            repo="openlifescienceai/medmcqa",
            description="193k medical MCQ questions with 21 subjects and 2400+ topics",
            splits=["train", "validation", "test"],
        ),
        DatasetConfig(
            name="medqa",
            repo="GBaker/MedQA-USMLE-4-options",
            description="11.5k USMLE-style questions",
            splits=["train", "test"],
        ),
        DatasetConfig(
            name="flashcards",
            repo="medalpaca/medical_meadow_medical_flashcards",
            description="33k medical Q&A pairs",
            splits=["train"],
        ),
        DatasetConfig(
            name="medqa_multiturn",
            repo="dynamoai-ml/MedQA-USMLE-4-MultiTurnRobust",
            description="MedQA with organ system categorization",
            splits=["train"],
        ),
    ]


def validate_medmcqa_record(record: dict[str, Any]) -> bool:
    """Validate a MedMCQA record has required fields."""
    for field_name in REQUIRED_MEDMCQA_FIELDS:
        if field_name not in record or record[field_name] is None:
            return False
    return True


def extract_medmcqa_topics(splits: list[str] | None = None) -> TopicStats:
    """Extract all unique topics from MedMCQA dataset."""
    ds = load_dataset("openlifescienceai/medmcqa")
    stats = TopicStats()

    if splits is None:
        splits = ["train"]

    for split in splits:
        if split not in ds:
            continue
        for example in ds[split]:
            if not validate_medmcqa_record(example):
                continue
            subject = example["subject_name"]
            topic = example["topic_name"]
            stats.add_topic(subject, topic)

    return stats


def filter_medqa_by_step(dataset: Any, step: str = "step1") -> list[dict[str, Any]]:
    """Filter MedQA dataset to specific USMLE step."""
    return [item for item in dataset if item.get("meta_info") == step]


def map_subject_to_taxonomy(subject: str) -> str:
    """Map a MedMCQA subject to a taxonomy category."""
    return SUBJECT_TO_TAXONOMY.get(subject, "other")


def generate_keywords(topics: list[str]) -> list[str]:
    """Generate searchable keywords from topic names."""
    keywords = []
    abbreviations = {
        "central nervous system": "cns",
        "cardiovascular": "cvs",
        "gastrointestinal": "gi",
        "genitourinary": "gu",
    }

    for topic in topics:
        topic_lower = topic.lower()
        words = re.findall(r"\b\w+\b", topic_lower)
        keywords.extend(words)

        for full, abbrev in abbreviations.items():
            if full in topic_lower:
                keywords.append(abbrev)

    return list(set(keywords))


def enrich_taxonomy(taxonomy_path: Path, topics_path: Path) -> dict[str, Any]:
    """Enrich taxonomy JSON with topic keywords."""
    taxonomy = json.loads(taxonomy_path.read_text())
    topics_data = json.loads(topics_path.read_text())

    topic_keywords: dict[str, list[str]] = {}
    for _subject, data in topics_data.items():
        for topic_name in data.get("topics", {}):
            keywords = generate_keywords([topic_name])
            for kw in keywords:
                if kw not in topic_keywords:
                    topic_keywords[kw] = []
                topic_keywords[kw].append(topic_name)

    for category in taxonomy.get("categories", []):
        for topic in category.get("topics", []):
            topic_name = topic.get("name", "").lower()
            existing_keywords = set(topic.get("keywords", []))

            for kw in list(topic_keywords.keys()):
                if kw in topic_name or topic_name in kw:
                    existing_keywords.add(kw)

            topic["keywords"] = list(existing_keywords)

    return taxonomy


class HuggingFaceIngestor:
    """Main class for ingesting Hugging Face datasets."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_dataset(self, config: DatasetConfig) -> list[Path]:
        """Download a single dataset and save to parquet."""
        self._ensure_output_dir()
        ds = load_dataset(config.repo)
        paths = []

        for split in ds:
            path = self.output_dir / f"{config.name}_{split}.parquet"
            ds[split].to_parquet(path)
            paths.append(path)

        return paths

    def download_all(self) -> dict[str, list[Path]]:
        """Download all configured datasets."""
        results = {}
        for config in get_dataset_configs():
            try:
                paths = self.download_dataset(config)
                results[config.name] = paths
            except Exception as e:
                typer.echo(f"Error downloading {config.name}: {e}", err=True)
        return results

    def extract_topics(self, output_path: Path) -> Path:
        """Extract topics from MedMCQA and save to JSON."""
        self._ensure_output_dir()
        stats = extract_medmcqa_topics(splits=["train", "validation", "test"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(stats.to_dict(), indent=2))
        return output_path


@app.command("extract-topics")
def extract_topics_command(
    output: Path = typer.Option(
        Path("data/hf/medmcqa_topics.json"),
        "--output",
        "-o",
        help="Output JSON file path",
    ),
) -> None:
    """Extract all unique topics from MedMCQA."""
    typer.echo("Extracting topics from MedMCQA...")
    stats = extract_medmcqa_topics(splits=["train"])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(stats.to_dict(), indent=2))

    result = stats.to_dict()
    for subject, data in sorted(result.items()):
        typer.echo(
            f"{subject}: {data['unique_topics']} topics, {data['total_questions']} questions"
        )

    summary = stats.get_summary()
    typer.echo(
        f"\nTotal: {summary['total_questions']} questions, {summary['total_subjects']} subjects, {summary['total_unique_topics']} unique topics"
    )
    typer.echo(f"Saved to {output}")


@app.command("download-all")
def download_all_command(
    output_dir: Path = typer.Option(
        Path("data/hf"),
        "--output-dir",
        "-o",
        help="Output directory for parquet files",
    ),
) -> None:
    """Download all datasets to Parquet."""
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = get_dataset_configs()
    for config in configs:
        typer.echo(f"Downloading {config.name}...")
        try:
            ds = load_dataset(config.repo)
            for split in ds:
                path = output_dir / f"{config.name}_{split}.parquet"
                ds[split].to_parquet(path)
                typer.echo(f"  {split}: {len(ds[split])} examples -> {path}")
        except Exception as e:
            typer.echo(f"  Error: {e}", err=True)


@app.command("enrich-taxonomy")
def enrich_taxonomy_command(
    taxonomy_path: Path = typer.Option(
        Path("data/taxonomies/usmle_step1_complete.json"),
        "--taxonomy",
        "-t",
        help="Taxonomy JSON file to enrich",
    ),
    topics_path: Path = typer.Option(
        Path("data/hf/medmcqa_topics.json"),
        "--topics",
        "-p",
        help="Topics JSON file from extract-topics",
    ),
    output_path: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (defaults to overwriting taxonomy)",
    ),
) -> None:
    """Add MedMCQA topics as keywords to taxonomy."""
    if not taxonomy_path.exists():
        typer.echo(f"Taxonomy file not found: {taxonomy_path}", err=True)
        raise typer.Exit(1)

    if not topics_path.exists():
        typer.echo(f"Topics file not found: {topics_path}", err=True)
        raise typer.Exit(1)

    enriched = enrich_taxonomy(taxonomy_path, topics_path)

    out = output_path or taxonomy_path
    out.write_text(json.dumps(enriched, indent=2))
    typer.echo(f"Enriched taxonomy saved to {out}")


if __name__ == "__main__":
    app()
