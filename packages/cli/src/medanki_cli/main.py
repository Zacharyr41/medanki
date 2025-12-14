import typer
from rich.console import Console

from medanki_cli import __version__
from medanki_cli.commands import generate, taxonomy, config


console = Console()

app = typer.Typer(
    name="medanki",
    help="MedAnki - Generate Anki flashcards from medical documents",
    add_completion=False,
)


def version_callback(value: bool):
    if value:
        console.print(f"MedAnki CLI version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    pass


app.add_typer(generate.app, name="generate")
app.add_typer(taxonomy.app, name="taxonomy")
app.add_typer(config.app, name="config")


if __name__ == "__main__":
    app()
