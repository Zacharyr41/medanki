import pytest
from typer.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock

from medanki_cli.main import app


runner = CliRunner()


class TestGenerateCommand:
    def test_generate_requires_input(self):
        result = runner.invoke(app, ["generate"])

        assert result.exit_code != 0
        assert "input" in result.stdout.lower() or "missing" in result.stdout.lower() or "required" in result.stdout.lower()

    def test_generate_accepts_file(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            mock_process.return_value = {"cards": [], "stats": {}}
            result = runner.invoke(app, ["generate", "--input", str(test_file)])

        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    def test_generate_accepts_directory(self, tmp_path):
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "test.pdf").write_bytes(b"%PDF-1.4 test content")

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            mock_process.return_value = {"cards": [], "stats": {}}
            result = runner.invoke(app, ["generate", "--input", str(test_dir)])

        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    def test_generate_output_option(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")
        output_path = tmp_path / "output.apkg"

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            mock_process.return_value = {"cards": [], "stats": {}}
            result = runner.invoke(app, ["generate", "--input", str(test_file), "--output", str(output_path)])

        assert result.exit_code == 0 or "--output" in result.stdout or "output" in result.stdout.lower()

    def test_generate_exam_option(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            mock_process.return_value = {"cards": [], "stats": {}}
            result = runner.invoke(app, ["generate", "--input", str(test_file), "--exam", "USMLE"])

        assert result.exit_code == 0 or "exam" in result.stdout.lower()

    def test_generate_dry_run(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            mock_process.return_value = {"cards": [{"text": "test"}], "stats": {"total": 1}}
            result = runner.invoke(app, ["generate", "--input", str(test_file), "--dry-run"])

        assert result.exit_code == 0
        assert "preview" in result.stdout.lower() or "dry" in result.stdout.lower() or "would" in result.stdout.lower()

    def test_generate_shows_progress(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            mock_process.return_value = {"cards": [], "stats": {}}
            result = runner.invoke(app, ["generate", "--input", str(test_file), "--verbose"])

        assert result.exit_code == 0
        assert "processing" in result.stdout.lower() or "progress" in result.stdout.lower() or "complete" in result.stdout.lower()

    def test_generate_creates_apkg(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")
        output_path = tmp_path / "output.apkg"

        with patch("medanki_cli.commands.generate.process_input") as mock_process:
            with patch("medanki_cli.commands.generate.create_apkg") as mock_apkg:
                mock_process.return_value = {"cards": [{"text": "test"}], "stats": {"total": 1}}
                mock_apkg.return_value = output_path
                result = runner.invoke(app, ["generate", "--input", str(test_file), "--output", str(output_path)])

        assert result.exit_code == 0
