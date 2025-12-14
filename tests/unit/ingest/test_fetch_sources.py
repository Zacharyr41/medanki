"""Tests for fetch_anking_sources script."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.fetch_anking_sources import (
    ANKING_REPO_URL,
    RESOURCE_SHEETS,
    clone_anking_repo,
    fetch_resource_sheets,
)


class TestCloneAnkingRepo:
    def test_skips_if_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            (target / "AnKing-v11").mkdir()

            result = clone_anking_repo(target)
            assert result is True

    @patch("scripts.fetch_anking_sources.subprocess.run")
    def test_clone_success(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            result = clone_anking_repo(target, shallow=True)

            assert result is True
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "git" in call_args
            assert "clone" in call_args
            assert "--depth" in call_args
            assert "1" in call_args
            assert ANKING_REPO_URL in call_args

    @patch("scripts.fetch_anking_sources.subprocess.run")
    def test_clone_failure(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Clone failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            result = clone_anking_repo(target)

            assert result is False


class TestFetchResourceSheets:
    @patch.dict("sys.modules", {"pandas": MagicMock()})
    def test_fetch_sheets_success(self):
        import sys

        mock_pd = sys.modules["pandas"]
        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 100
        mock_pd.read_csv.return_value = mock_df

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            results = fetch_resource_sheets(target)

            assert all(results.values())
            assert len(results) == len(RESOURCE_SHEETS)

    @patch.dict("sys.modules", {"pandas": MagicMock()})
    def test_fetch_sheets_failure(self):
        import sys

        mock_pd = sys.modules["pandas"]
        mock_pd.read_csv.side_effect = Exception("Network error")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            results = fetch_resource_sheets(target)

            assert all(v is False for v in results.values())

    @patch.dict("sys.modules", {"pandas": MagicMock()})
    def test_creates_target_directory(self):
        import sys

        mock_pd = sys.modules["pandas"]
        mock_df = MagicMock()
        mock_df.__len__ = lambda self: 10
        mock_pd.read_csv.return_value = mock_df

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "nested" / "sheets"
            fetch_resource_sheets(target)

            assert target.exists()


class TestResourceSheetUrls:
    def test_all_sheets_have_urls(self):
        assert "boards_beyond" in RESOURCE_SHEETS
        assert "pathoma" in RESOURCE_SHEETS
        assert "sketchy" in RESOURCE_SHEETS

    def test_urls_are_google_sheets(self):
        for url in RESOURCE_SHEETS.values():
            assert "docs.google.com/spreadsheets" in url
            assert "export?format=csv" in url
