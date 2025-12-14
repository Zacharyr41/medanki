from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


app = typer.Typer(help="Generate Anki flashcards from medical documents")
console = Console()


def process_input(input_path: Path, exam: Optional[str] = None) -> dict:
    return {"cards": [], "stats": {"total": 0}}


def create_apkg(cards: list, output_path: Path) -> Path:
    output_path.touch()
    return output_path


@app.callback(invoke_without_command=True)
def generate(
    ctx: typer.Context,
    input_path: Path = typer.Option(
        None,
        "--input",
        "-i",
        help="Input file or directory path",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output .apkg file path",
    ),
    exam: Optional[str] = typer.Option(
        None,
        "--exam",
        "-e",
        help="Filter by exam type (e.g., USMLE, COMLEX)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview without saving",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show detailed progress",
    ),
):
    if ctx.invoked_subcommand is not None:
        return

    if input_path is None:
        console.print("[red]Error: Missing required option --input[/red]")
        raise typer.Exit(code=1)

    if not input_path.exists():
        console.print(f"[red]Error: Input path does not exist: {input_path}[/red]")
        raise typer.Exit(code=1)

    if verbose:
        console.print(f"[blue]Processing {input_path}...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=not verbose,
    ) as progress:
        task = progress.add_task("Processing documents...", total=None)

        result = process_input(input_path, exam)
        cards = result.get("cards", [])
        stats = result.get("stats", {})

        progress.update(task, completed=True)

    if dry_run:
        console.print("\n[yellow]Dry run - Preview mode[/yellow]")
        console.print(f"Would generate {len(cards)} cards")
        if cards:
            console.print("\n[bold]Sample cards:[/bold]")
            for card in cards[:3]:
                console.print(f"  - {card.get('text', 'N/A')[:50]}...")
        return

    if output is None:
        output = Path.cwd() / "output.apkg"

    if cards:
        create_apkg(cards, output)
        console.print(f"\n[green]Created {output}[/green]")
    else:
        console.print("[yellow]No cards generated[/yellow]")

    if verbose:
        console.print("\n[bold]Complete![/bold]")
        console.print(f"  Total cards: {len(cards)}")
