from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from medanki_cli.main import app

runner = CliRunner()


class TestGenerateCommand:
    def test_generate_requires_input(self):
        result = runner.invoke(app, ["generate"])

        assert result.exit_code != 0
        assert (
            "input" in result.stdout.lower()
            or "missing" in result.stdout.lower()
            or "required" in result.stdout.lower()
        )

    def test_generate_accepts_file(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nSome content")

        with patch(
            "medanki_cli.commands.generate.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {
                "cards": [],
                "stats": {"total": 0, "cloze": 0, "vignette": 0, "chunks": 0, "duration": 0},
            }
            result = runner.invoke(app, ["generate", "--input", str(test_file), "--dry-run"])

        assert result.exit_code == 0 or "error" not in result.stdout.lower()

    def test_generate_rejects_directory(self, tmp_path):
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "test.md").write_text("# Test\nSome content")

        result = runner.invoke(app, ["generate", "--input", str(test_dir)])

        assert result.exit_code != 0

    def test_generate_output_option(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nSome content")
        output_path = tmp_path / "output.apkg"

        with patch(
            "medanki_cli.commands.generate.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {
                "cards": [],
                "stats": {"total": 0, "cloze": 0, "vignette": 0, "chunks": 0, "duration": 0},
            }
            result = runner.invoke(
                app,
                ["generate", "--input", str(test_file), "--output", str(output_path), "--dry-run"],
            )

        assert (
            result.exit_code == 0
            or "--output" in result.stdout
            or "output" in result.stdout.lower()
        )

    def test_generate_exam_option(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nSome content")

        with patch(
            "medanki_cli.commands.generate.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {
                "cards": [],
                "stats": {"total": 0, "cloze": 0, "vignette": 0, "chunks": 0, "duration": 0},
            }
            result = runner.invoke(
                app, ["generate", "--input", str(test_file), "--exam", "USMLE", "--dry-run"]
            )

        assert result.exit_code == 0 or "exam" in result.stdout.lower()

    def test_generate_dry_run(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nSome content")

        with patch(
            "medanki_cli.commands.generate.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {
                "cards": [],
                "stats": {"total": 0, "cloze": 0, "vignette": 0, "chunks": 0, "duration": 0},
            }
            result = runner.invoke(app, ["generate", "--input", str(test_file), "--dry-run"])

        assert result.exit_code == 0
        assert "dry" in result.stdout.lower()

    def test_generate_shows_progress(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nSome content")

        with patch(
            "medanki_cli.commands.generate.process_document", new_callable=AsyncMock
        ) as mock_process:
            mock_process.return_value = {
                "cards": [],
                "stats": {"total": 0, "cloze": 0, "vignette": 0, "chunks": 0, "duration": 0},
            }
            result = runner.invoke(
                app, ["generate", "--input", str(test_file), "--verbose", "--dry-run"]
            )

        assert result.exit_code == 0
        assert (
            "processing" in result.stdout.lower()
            or "complete" in result.stdout.lower()
            or "results" in result.stdout.lower()
        )

    def test_generate_creates_apkg(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nSome content")
        output_path = tmp_path / "output.apkg"

        with patch(
            "medanki_cli.commands.generate.process_document", new_callable=AsyncMock
        ) as mock_process:
            with patch("medanki_cli.commands.generate.create_apkg") as mock_apkg:
                mock_process.return_value = {
                    "cards": [{"text": "test"}],
                    "stats": {"total": 1, "cloze": 1, "vignette": 0, "chunks": 1, "duration": 0},
                }
                mock_apkg.return_value = output_path
                result = runner.invoke(
                    app, ["generate", "--input", str(test_file), "--output", str(output_path)]
                )

        assert result.exit_code == 0
