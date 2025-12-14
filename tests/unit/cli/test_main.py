from typer.testing import CliRunner

from medanki_cli.main import app

runner = CliRunner()


class TestCLIMain:
    def test_cli_has_help(self):
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Usage" in result.stdout or "usage" in result.stdout.lower()

    def test_cli_has_version(self):
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.stdout

    def test_cli_has_generate_command(self):
        result = runner.invoke(app, ["generate", "--help"])

        assert result.exit_code == 0
        assert "generate" in result.stdout.lower() or "Generate" in result.stdout

    def test_cli_has_taxonomy_command(self):
        result = runner.invoke(app, ["taxonomy", "--help"])

        assert result.exit_code == 0
        assert "taxonomy" in result.stdout.lower() or "Taxonomy" in result.stdout

    def test_cli_has_config_command(self):
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "config" in result.stdout.lower() or "Config" in result.stdout
