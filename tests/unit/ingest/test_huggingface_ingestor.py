"""Tests for Hugging Face dataset ingestion pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from scripts.ingest.huggingface import (
    DatasetConfig,
    HuggingFaceIngestor,
    TopicStats,
    extract_medmcqa_topics,
    get_dataset_configs,
)


class MockDataset:
    """Mock HuggingFace dataset for testing."""

    def __init__(self, data: list[dict[str, Any]], split: str = "train"):
        self._data = data
        self._split = split

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key: str | int):
        if isinstance(key, str):
            return [item[key] for item in self._data]
        return self._data[key]

    def filter(self, fn):
        filtered = [item for item in self._data if fn(item)]
        return MockDataset(filtered, self._split)

    def to_parquet(self, path: Path) -> None:
        pass

    def keys(self):
        return [self._split]


class MockDatasetDict:
    """Mock HuggingFace DatasetDict."""

    def __init__(self, datasets: dict[str, MockDataset]):
        self._datasets = datasets

    def __getitem__(self, key: str) -> MockDataset:
        return self._datasets[key]

    def __contains__(self, key: str) -> bool:
        return key in self._datasets

    def __iter__(self):
        return iter(self._datasets)

    def keys(self):
        return self._datasets.keys()


@pytest.fixture
def medmcqa_sample_data() -> list[dict[str, Any]]:
    """Sample MedMCQA data for testing."""
    return [
        {
            "id": "1",
            "question": "What structure passes through the foramen magnum?",
            "opa": "Spinal cord",
            "opb": "Vagus nerve",
            "opc": "Accessory nerve",
            "opd": "Hypoglossal nerve",
            "cop": 0,
            "choice_type": "single",
            "exp": "The spinal cord passes through the foramen magnum.",
            "subject_name": "Anatomy",
            "topic_name": "Nervous system",
        },
        {
            "id": "2",
            "question": "What is the function of insulin?",
            "opa": "Increase blood glucose",
            "opb": "Decrease blood glucose",
            "opc": "Increase blood pressure",
            "opd": "Decrease heart rate",
            "cop": 1,
            "choice_type": "single",
            "exp": "Insulin lowers blood glucose by promoting uptake.",
            "subject_name": "Physiology",
            "topic_name": "Endocrine system",
        },
        {
            "id": "3",
            "question": "What is the target of warfarin?",
            "opa": "Vitamin K",
            "opb": "Factor Xa",
            "opc": "Thrombin",
            "opd": "Plasmin",
            "cop": 0,
            "choice_type": "single",
            "exp": "Warfarin inhibits vitamin K epoxide reductase.",
            "subject_name": "Pharmacology",
            "topic_name": "Anticoagulants",
        },
        {
            "id": "4",
            "question": "Which cranial nerve innervates the lateral rectus?",
            "opa": "III",
            "opb": "IV",
            "opc": "V",
            "opd": "VI",
            "cop": 3,
            "choice_type": "single",
            "exp": "CN VI (abducens) innervates the lateral rectus.",
            "subject_name": "Anatomy",
            "topic_name": "Nervous system",
        },
    ]


@pytest.fixture
def medqa_sample_data() -> list[dict[str, Any]]:
    """Sample MedQA data for testing."""
    return [
        {
            "question": "A 45-year-old man presents with chest pain...",
            "answer": "Myocardial infarction",
            "options": {
                "A": "Angina pectoris",
                "B": "Myocardial infarction",
                "C": "Pericarditis",
                "D": "Pulmonary embolism",
            },
            "meta_info": "step1",
            "answer_idx": "B",
        },
        {
            "question": "A patient presents with jaundice...",
            "answer": "Hepatitis B",
            "options": {
                "A": "Hepatitis A",
                "B": "Hepatitis B",
                "C": "Hepatitis C",
                "D": "Alcoholic hepatitis",
            },
            "meta_info": "step2&3",
            "answer_idx": "B",
        },
    ]


@pytest.fixture
def flashcards_sample_data() -> list[dict[str, Any]]:
    """Sample medical flashcards data."""
    return [
        {
            "input": "What is the mechanism of action of aspirin?",
            "output": "Aspirin irreversibly inhibits COX-1 and COX-2.",
            "instruction": "Answer the medical question.",
        },
        {
            "input": "What are the symptoms of hyperthyroidism?",
            "output": "Weight loss, tremor, heat intolerance, tachycardia.",
            "instruction": "Answer the medical question.",
        },
    ]


@pytest.fixture
def mock_medmcqa(medmcqa_sample_data: list[dict[str, Any]]) -> MockDatasetDict:
    """Create mock MedMCQA dataset."""
    return MockDatasetDict(
        {
            "train": MockDataset(medmcqa_sample_data, "train"),
            "validation": MockDataset(medmcqa_sample_data[:2], "validation"),
            "test": MockDataset(medmcqa_sample_data[:1], "test"),
        }
    )


@pytest.fixture
def mock_medqa(medqa_sample_data: list[dict[str, Any]]) -> MockDatasetDict:
    """Create mock MedQA dataset."""
    return MockDatasetDict({"train": MockDataset(medqa_sample_data, "train")})


class TestDatasetConfig:
    """Tests for DatasetConfig model."""

    def test_create_config(self) -> None:
        """DatasetConfig can be created with required fields."""
        config = DatasetConfig(
            name="medmcqa",
            repo="openlifescienceai/medmcqa",
            description="Medical MCQ dataset",
        )
        assert config.name == "medmcqa"
        assert config.repo == "openlifescienceai/medmcqa"

    def test_get_dataset_configs(self) -> None:
        """get_dataset_configs returns all configured datasets."""
        configs = get_dataset_configs()
        assert len(configs) >= 3
        names = [c.name for c in configs]
        assert "medmcqa" in names
        assert "medqa" in names
        assert "flashcards" in names


class TestTopicStats:
    """Tests for TopicStats model."""

    def test_topic_stats_creation(self) -> None:
        """TopicStats tracks topic counts correctly."""
        stats = TopicStats()
        stats.add_topic("Anatomy", "Nervous system")
        stats.add_topic("Anatomy", "Nervous system")
        stats.add_topic("Anatomy", "Cardiovascular")
        stats.add_topic("Physiology", "Endocrine")

        assert stats.get_subject_count("Anatomy") == 3
        assert stats.get_subject_count("Physiology") == 1
        assert stats.get_unique_topics("Anatomy") == 2
        assert stats.get_topic_count("Anatomy", "Nervous system") == 2

    def test_topic_stats_to_dict(self) -> None:
        """TopicStats can be serialized to dict."""
        stats = TopicStats()
        stats.add_topic("Anatomy", "Nervous system")
        stats.add_topic("Anatomy", "Cardiovascular")

        result = stats.to_dict()
        assert "Anatomy" in result
        assert result["Anatomy"]["total_questions"] == 2
        assert result["Anatomy"]["unique_topics"] == 2
        assert "Nervous system" in result["Anatomy"]["topics"]


class TestExtractMedmcqaTopics:
    """Tests for extracting topics from MedMCQA dataset."""

    def test_extracts_all_subjects(
        self, mock_medmcqa: MockDatasetDict, medmcqa_sample_data: list[dict[str, Any]]
    ) -> None:
        """Extracts all unique subjects from dataset."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            stats = extract_medmcqa_topics()

        subjects = list(stats.to_dict().keys())
        expected_subjects = {"Anatomy", "Physiology", "Pharmacology"}
        assert set(subjects) == expected_subjects

    def test_counts_topics_per_subject(self, mock_medmcqa: MockDatasetDict) -> None:
        """Correctly counts topics within each subject."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            stats = extract_medmcqa_topics()

        result = stats.to_dict()
        assert result["Anatomy"]["total_questions"] == 2
        assert result["Anatomy"]["unique_topics"] == 1
        assert result["Anatomy"]["topics"]["Nervous system"] == 2

    def test_handles_multiple_splits(self, mock_medmcqa: MockDatasetDict) -> None:
        """Can process multiple splits if specified."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            stats = extract_medmcqa_topics(splits=["train", "validation"])

        result = stats.to_dict()
        assert result["Anatomy"]["total_questions"] >= 2


class TestHuggingFaceIngestor:
    """Tests for the main HuggingFaceIngestor class."""

    def test_ingestor_initialization(self, tmp_path: Path) -> None:
        """Ingestor initializes with output directory."""
        ingestor = HuggingFaceIngestor(output_dir=tmp_path)
        assert ingestor.output_dir == tmp_path

    def test_ingestor_creates_output_dir(self, tmp_path: Path) -> None:
        """Ingestor creates output directory if missing."""
        output_dir = tmp_path / "new_dir" / "nested"
        ingestor = HuggingFaceIngestor(output_dir=output_dir)
        ingestor._ensure_output_dir()
        assert output_dir.exists()

    def test_download_dataset(
        self,
        mock_medmcqa: MockDatasetDict,
        tmp_path: Path,
    ) -> None:
        """Downloads dataset and saves to parquet."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            ingestor = HuggingFaceIngestor(output_dir=tmp_path)
            config = DatasetConfig(
                name="medmcqa",
                repo="openlifescienceai/medmcqa",
                description="Test",
            )
            paths = ingestor.download_dataset(config)

        assert len(paths) == 3
        assert any("train" in str(p) for p in paths)

    def test_download_all_datasets(
        self,
        mock_medmcqa: MockDatasetDict,
        mock_medqa: MockDatasetDict,
        tmp_path: Path,
    ) -> None:
        """Downloads all configured datasets."""

        def mock_load(repo: str, **kwargs):
            if "medmcqa" in repo:
                return mock_medmcqa
            return mock_medqa

        with patch("scripts.ingest.huggingface.load_dataset", side_effect=mock_load):
            ingestor = HuggingFaceIngestor(output_dir=tmp_path)
            results = ingestor.download_all()

        assert len(results) >= 2

    def test_extract_topics_to_json(
        self,
        mock_medmcqa: MockDatasetDict,
        tmp_path: Path,
    ) -> None:
        """Extracts topics and saves to JSON file."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            ingestor = HuggingFaceIngestor(output_dir=tmp_path)
            output_path = ingestor.extract_topics(tmp_path / "topics.json")

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "Anatomy" in data
        assert "topics" in data["Anatomy"]

    def test_filter_step1_questions(
        self,
        mock_medqa: MockDatasetDict,
    ) -> None:
        """Filters MedQA to only Step 1 questions."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medqa):
            from scripts.ingest.huggingface import filter_medqa_by_step

            step1_data = filter_medqa_by_step(mock_medqa["train"], step="step1")

        assert len(step1_data) == 1
        assert step1_data[0]["meta_info"] == "step1"


class TestTopicEnrichment:
    """Tests for taxonomy enrichment from topics."""

    def test_map_subject_to_taxonomy(self) -> None:
        """Maps MedMCQA subjects to taxonomy categories."""
        from scripts.ingest.huggingface import map_subject_to_taxonomy

        mappings = {
            "Anatomy": "organ_systems",
            "Physiology": "organ_systems",
            "Biochemistry": "biochemistry_metabolism",
            "Pharmacology": "pharmacology",
            "Pathology": "pathology",
            "Microbiology": "microbiology",
        }

        for subject, expected in mappings.items():
            result = map_subject_to_taxonomy(subject)
            assert result == expected, f"Expected {expected} for {subject}, got {result}"

    def test_generate_keywords_from_topics(self) -> None:
        """Generates searchable keywords from topic names."""
        from scripts.ingest.huggingface import generate_keywords

        topics = ["Urinary tract", "Central nervous system", "Cardiovascular system"]
        keywords = generate_keywords(topics)

        assert "urinary" in keywords
        assert "tract" in keywords
        assert "cns" in keywords or "central nervous system" in keywords
        assert "cardiovascular" in keywords

    def test_enrich_taxonomy_structure(self, tmp_path: Path) -> None:
        """Enriches taxonomy JSON with topic keywords."""
        from scripts.ingest.huggingface import enrich_taxonomy

        taxonomy = {
            "id": "usmle_step1",
            "categories": [
                {
                    "id": "organ_systems",
                    "name": "Organ Systems",
                    "topics": [
                        {
                            "id": "cardiovascular",
                            "name": "Cardiovascular",
                            "keywords": ["heart"],
                        }
                    ],
                }
            ],
        }

        topics_data = {
            "Anatomy": {
                "topics": {
                    "Cardiovascular system": 100,
                    "Heart anatomy": 50,
                }
            }
        }

        taxonomy_path = tmp_path / "taxonomy.json"
        taxonomy_path.write_text(json.dumps(taxonomy))

        topics_path = tmp_path / "topics.json"
        topics_path.write_text(json.dumps(topics_data))

        result = enrich_taxonomy(taxonomy_path, topics_path)

        cardio_topic = result["categories"][0]["topics"][0]
        assert "cardiovascular" in cardio_topic["keywords"]
        assert "heart" in cardio_topic["keywords"]


class TestCLICommands:
    """Tests for CLI command functions."""

    def test_extract_topics_command(
        self,
        mock_medmcqa: MockDatasetDict,
        tmp_path: Path,
    ) -> None:
        """extract-topics command works correctly."""
        from scripts.ingest.huggingface import extract_topics_command

        output = tmp_path / "output.json"

        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            extract_topics_command(output=output)

        assert output.exists()
        data = json.loads(output.read_text())
        assert len(data) > 0

    def test_download_all_command(
        self,
        mock_medmcqa: MockDatasetDict,
        tmp_path: Path,
    ) -> None:
        """download-all command downloads datasets."""
        from scripts.ingest.huggingface import download_all_command

        def mock_load(repo: str, **kwargs):
            return mock_medmcqa

        with patch("scripts.ingest.huggingface.load_dataset", side_effect=mock_load):
            download_all_command(output_dir=tmp_path)

    def test_enrich_taxonomy_command(
        self,
        tmp_path: Path,
    ) -> None:
        """enrich-taxonomy command updates taxonomy file."""
        from typer.testing import CliRunner

        from scripts.ingest.huggingface import app

        taxonomy = {"categories": []}
        topics = {"Anatomy": {"topics": {}}}

        taxonomy_path = tmp_path / "taxonomy.json"
        taxonomy_path.write_text(json.dumps(taxonomy))

        topics_path = tmp_path / "topics.json"
        topics_path.write_text(json.dumps(topics))

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "enrich-taxonomy",
                "--taxonomy",
                str(taxonomy_path),
                "--topics",
                str(topics_path),
            ],
        )
        assert result.exit_code == 0


class TestDataValidation:
    """Tests for data validation."""

    def test_validates_medmcqa_structure(self, medmcqa_sample_data: list[dict[str, Any]]) -> None:
        """Validates MedMCQA has required fields."""
        from scripts.ingest.huggingface import validate_medmcqa_record

        for record in medmcqa_sample_data:
            assert validate_medmcqa_record(record) is True

    def test_rejects_invalid_record(self) -> None:
        """Rejects records missing required fields."""
        from scripts.ingest.huggingface import validate_medmcqa_record

        invalid_record = {"question": "What?"}
        assert validate_medmcqa_record(invalid_record) is False

    def test_handles_missing_topic(self) -> None:
        """Handles records with missing topic_name gracefully."""
        from scripts.ingest.huggingface import validate_medmcqa_record

        record = {
            "subject_name": "Anatomy",
            "topic_name": None,
            "question": "What?",
        }
        assert validate_medmcqa_record(record) is False


class TestStatisticsGeneration:
    """Tests for statistics generation."""

    def test_generates_summary_stats(
        self,
        mock_medmcqa: MockDatasetDict,
    ) -> None:
        """Generates summary statistics for dataset."""
        with patch("scripts.ingest.huggingface.load_dataset", return_value=mock_medmcqa):
            stats = extract_medmcqa_topics()
            summary = stats.get_summary()

        assert "total_questions" in summary
        assert "total_subjects" in summary
        assert "total_unique_topics" in summary
        assert summary["total_questions"] == 4
        assert summary["total_subjects"] == 3

    def test_sorts_topics_by_frequency(self) -> None:
        """Topics sorted by frequency (descending)."""
        stats = TopicStats()
        stats.add_topic("Anatomy", "Rare topic")
        for _ in range(10):
            stats.add_topic("Anatomy", "Common topic")
        for _ in range(5):
            stats.add_topic("Anatomy", "Medium topic")

        result = stats.to_dict()
        topics = list(result["Anatomy"]["topics"].keys())
        assert topics[0] == "Common topic"
        assert topics[1] == "Medium topic"
        assert topics[2] == "Rare topic"
