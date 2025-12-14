from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from medanki_cli.main import app

runner = CliRunner()


class TestConfigCommand:
    def test_config_show(self):
        with patch("medanki_cli.commands.config.get_config") as mock_config:
            mock_config.return_value = {
                "output_dir": "/tmp/medanki",
                "default_exam": "USMLE",
                "verbose": False,
            }
            result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "output_dir" in result.stdout or "USMLE" in result.stdout

    def test_config_set(self):
        with patch("medanki_cli.commands.config.set_config") as mock_set:
            mock_set.return_value = True
            result = runner.invoke(app, ["config", "set", "default_exam", "COMLEX"])

        assert result.exit_code == 0
        mock_set.assert_called_once_with("default_exam", "COMLEX")

    def test_config_path(self):
        with patch("medanki_cli.commands.config.get_config_path") as mock_path:
            mock_path.return_value = Path.home() / ".config" / "medanki" / "config.toml"
            result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert "config" in result.stdout.lower() or ".toml" in result.stdout
