"""Tests for taxonomy CLI commands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from medanki_cli.main import app

runner = CliRunner()


@pytest.fixture
def mock_repo():
    """Create a mock repository."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    mock.list_exams = AsyncMock(return_value=[
        {"id": "MCAT", "name": "MCAT", "version": "2024"},
        {"id": "USMLE_STEP1", "name": "USMLE Step 1", "version": "2024"},
    ])
    mock.list_nodes_by_exam = AsyncMock(return_value=[
        {"id": "MCAT_FC1", "title": "Biomolecules", "node_type": "foundational_concept", "exam_id": "MCAT"},
        {"id": "MCAT_1A", "title": "Proteins", "node_type": "content_category", "exam_id": "MCAT", "parent_id": "MCAT_FC1"},
    ])
    mock.list_nodes_by_type = AsyncMock(return_value=[
        {"id": "MCAT_FC1", "title": "Biomolecules", "node_type": "foundational_concept", "exam_id": "MCAT"},
    ])
    mock.search_nodes_by_keyword = AsyncMock(return_value=[
        {"id": "MCAT_FC1", "title": "Biomolecules", "node_type": "foundational_concept", "exam_id": "MCAT"},
    ])
    mock.get_node = AsyncMock(return_value={
        "id": "MCAT_FC1",
        "title": "Biomolecules",
        "node_type": "foundational_concept",
        "exam_id": "MCAT",
        "code": "FC1",
    })
    mock.get_path = AsyncMock(return_value=["Biomolecules"])
    mock.get_keywords_for_node = AsyncMock(return_value=[
        {"keyword": "protein", "keyword_type": "general"},
        {"keyword": "enzyme", "keyword_type": "general"},
    ])
    mock.get_children = AsyncMock(return_value=[
        {"id": "MCAT_1A", "title": "Proteins", "node_type": "content_category"},
    ])
    mock.get_descendants = AsyncMock(return_value=[])
    return mock


class TestTaxonomyBuildCommand:
    """Tests for taxonomy build command."""

    def test_build_help(self):
        """Build command shows help."""
        result = runner.invoke(app, ["taxonomy", "build", "--help"])
        assert result.exit_code == 0
        assert "Build taxonomy database" in result.stdout

    def test_build_creates_database(self, tmp_path):
        """Build command creates database file."""
        db_path = tmp_path / "test.db"
        mcat_json = tmp_path / "mcat.json"
        usmle_json = tmp_path / "usmle.json"

        mcat_json.write_text(json.dumps({
            "exam": "MCAT",
            "version": "2024",
            "foundational_concepts": [
                {"id": "FC1", "title": "Test", "keywords": ["test"], "categories": []},
            ],
        }))
        usmle_json.write_text(json.dumps({
            "exam": "USMLE_STEP1",
            "version": "2024",
            "systems": [],
        }))

        result = runner.invoke(app, [
            "taxonomy", "build",
            "--db", str(db_path),
            "--mcat", str(mcat_json),
            "--usmle", str(usmle_json),
        ])

        assert result.exit_code == 0
        assert db_path.exists()


class TestTaxonomyListCommand:
    """Tests for taxonomy list command."""

    def test_list_requires_database(self, tmp_path):
        """List command fails without database."""
        db_path = tmp_path / "nonexistent.db"
        result = runner.invoke(app, ["taxonomy", "list", "--db", str(db_path)])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_list_shows_topics(self, mock_repo, tmp_path):
        """List command shows taxonomy topics."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with patch("medanki_cli.commands.taxonomy.get_repo", return_value=mock_repo):
            result = runner.invoke(app, ["taxonomy", "list", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Biomolecules" in result.stdout


class TestTaxonomySearchCommand:
    """Tests for taxonomy search command."""

    def test_search_requires_database(self, tmp_path):
        """Search command fails without database."""
        db_path = tmp_path / "nonexistent.db"
        result = runner.invoke(app, ["taxonomy", "search", "test", "--db", str(db_path)])
        assert result.exit_code == 1

    def test_search_finds_results(self, mock_repo, tmp_path):
        """Search command finds matching nodes."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with patch("medanki_cli.commands.taxonomy.get_repo", return_value=mock_repo):
            result = runner.invoke(app, ["taxonomy", "search", "protein", "--db", str(db_path)])

        assert result.exit_code == 0


class TestTaxonomyShowCommand:
    """Tests for taxonomy show command."""

    def test_show_requires_database(self, tmp_path):
        """Show command fails without database."""
        db_path = tmp_path / "nonexistent.db"
        result = runner.invoke(app, ["taxonomy", "show", "FC1", "--db", str(db_path)])
        assert result.exit_code == 1

    def test_show_displays_node(self, mock_repo, tmp_path):
        """Show command displays node details."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with patch("medanki_cli.commands.taxonomy.get_repo", return_value=mock_repo):
            result = runner.invoke(app, ["taxonomy", "show", "MCAT_FC1", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Biomolecules" in result.stdout

    def test_show_not_found(self, mock_repo, tmp_path):
        """Show command handles missing node."""
        db_path = tmp_path / "test.db"
        db_path.touch()
        mock_repo.get_node = AsyncMock(return_value=None)

        with patch("medanki_cli.commands.taxonomy.get_repo", return_value=mock_repo):
            result = runner.invoke(app, ["taxonomy", "show", "NONEXISTENT", "--db", str(db_path)])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestTaxonomyStatsCommand:
    """Tests for taxonomy stats command."""

    def test_stats_requires_database(self, tmp_path):
        """Stats command fails without database."""
        db_path = tmp_path / "nonexistent.db"
        result = runner.invoke(app, ["taxonomy", "stats", "--db", str(db_path)])
        assert result.exit_code == 1


class TestTaxonomyTreeCommand:
    """Tests for taxonomy tree command."""

    def test_tree_requires_database(self, tmp_path):
        """Tree command fails without database."""
        db_path = tmp_path / "nonexistent.db"
        result = runner.invoke(app, ["taxonomy", "tree", "--db", str(db_path)])
        assert result.exit_code == 1
