from unittest.mock import patch

from typer.testing import CliRunner

from medanki_cli.main import app

runner = CliRunner()


class TestTaxonomyCommand:
    def test_taxonomy_list(self):
        with patch("medanki_cli.commands.taxonomy.get_topics") as mock_topics:
            mock_topics.return_value = [
                {"id": "1", "name": "Cardiology", "exam": "USMLE"},
                {"id": "2", "name": "Neurology", "exam": "USMLE"},
            ]
            result = runner.invoke(app, ["taxonomy", "list"])

        assert result.exit_code == 0
        assert "Cardiology" in result.stdout or "cardiology" in result.stdout.lower()

    def test_taxonomy_search(self):
        with patch("medanki_cli.commands.taxonomy.search_topics") as mock_search:
            mock_search.return_value = [
                {"id": "1", "name": "Cardiology", "exam": "USMLE"},
            ]
            result = runner.invoke(app, ["taxonomy", "search", "cardio"])

        assert result.exit_code == 0
        assert "Cardiology" in result.stdout or "cardio" in result.stdout.lower()

    def test_taxonomy_show(self):
        with patch("medanki_cli.commands.taxonomy.get_topic_details") as mock_details:
            mock_details.return_value = {
                "id": "1",
                "name": "Cardiology",
                "exam": "USMLE",
                "subtopics": ["Heart Failure", "Arrhythmias"],
            }
            result = runner.invoke(app, ["taxonomy", "show", "1"])

        assert result.exit_code == 0
        assert "Cardiology" in result.stdout or "Heart Failure" in result.stdout

    def test_taxonomy_filter_exam(self):
        with patch("medanki_cli.commands.taxonomy.get_topics") as mock_topics:
            mock_topics.return_value = [
                {"id": "1", "name": "Cardiology", "exam": "USMLE"},
            ]
            result = runner.invoke(app, ["taxonomy", "list", "--exam", "USMLE"])

        assert result.exit_code == 0
        mock_topics.assert_called_once()
        call_kwargs = mock_topics.call_args
        assert call_kwargs[1].get("exam") == "USMLE" or "USMLE" in str(call_kwargs)
