"""Generate command for creating Anki flashcards."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="Generate Anki flashcards from medical documents")
console = Console()


async def process_document(
    input_path: Path,
    exam: str | None,
    max_cards: int,
    enable_vignettes: bool,
    on_progress=None,
):
    """Process a document and generate flashcards."""
    from medanki.factory import ServiceConfig, get_factory
    from medanki.generation.service import GenerationConfig

    config = ServiceConfig(
        taxonomy_dir=Path("data/taxonomies"),
    )
    factory = get_factory(config)

    ingestion = factory.get_ingestion_service()
    chunking = factory.get_chunking_service()

    if on_progress:
        on_progress("ingestion", 0.1)

    document = await ingestion.ingest_file(input_path)

    if on_progress:
        on_progress("chunking", 0.3)

    chunks = chunking.chunk(document)

    if not chunks:
        return {"cards": [], "stats": {"total": 0, "chunks": 0}}

    if on_progress:
        on_progress("generation", 0.5)

    generation_service = factory.create_generation_service()
    gen_config = GenerationConfig(
        enable_cloze=True,
        enable_vignettes=enable_vignettes,
        max_cloze_per_chunk=max_cards,
        max_vignette_per_chunk=1 if enable_vignettes else 0,
    )

    class ChunkAdapter:
        def __init__(self, chunk):
            self.id = uuid4()
            self.content = chunk.text
            self.text = chunk.text

    adapted_chunks = [ChunkAdapter(c) for c in chunks]

    result = await generation_service.generate_cards(
        chunks=adapted_chunks,
        config=gen_config,
    )

    if on_progress:
        on_progress("complete", 1.0)

    return {
        "cards": result.cards,
        "stats": {
            "total": result.stats.total_cards,
            "cloze": result.stats.cloze_count,
            "vignette": result.stats.vignette_count,
            "chunks": result.stats.chunks_processed,
            "duration": result.stats.duration_seconds,
        },
    }


def create_apkg(cards: list, output_path: Path, exam: str | None = None) -> Path:
    """Create an Anki package from cards."""
    import genanki

    from medanki.export.deck import DeckBuilder
    from medanki.models.cards import ClozeCard, VignetteCard

    deck_name = f"MedAnki::{exam or 'General'}"
    builder = DeckBuilder(name=deck_name)

    class CardAdapter:
        def __init__(self, card):
            if isinstance(card, ClozeCard):
                self.text = card.text
                self.extra = ""
                self.source_chunk_id = str(card.source_chunk_id)
                self.tags = [card.topic_id] if card.topic_id else []
            elif isinstance(card, VignetteCard):
                self.front = f"{card.stem}\n\n{card.question}"
                options_text = "\n".join(f"{opt.letter}. {opt.text}" for opt in card.options)
                self.front += f"\n\n{options_text}"
                self.answer = card.answer
                self.explanation = card.explanation
                self.distinguishing_feature = None
                self.source_chunk_id = str(card.source_chunk_id)
                self.tags = [card.topic_id] if card.topic_id else []

    for card in cards:
        adapted = CardAdapter(card)
        if isinstance(card, ClozeCard):
            builder.add_cloze_card(adapted)
        elif isinstance(card, VignetteCard):
            builder.add_vignette_card(adapted)

    deck = builder.build()
    package = genanki.Package(deck)
    package.write_to_file(str(output_path))
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
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output .apkg file path",
    ),
    exam: str | None = typer.Option(
        None,
        "--exam",
        "-e",
        help="Target exam: MCAT, USMLE_STEP1",
    ),
    max_cards: int = typer.Option(
        3,
        "--max-cards",
        "-m",
        help="Maximum cards per chunk",
    ),
    vignettes: bool = typer.Option(
        False,
        "--vignettes/--no-vignettes",
        help="Generate clinical vignette cards",
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
    """Generate Anki flashcards from medical documents.

    Examples:

        medanki generate -i lecture.pdf -o cards.apkg

        medanki generate -i notes.md --exam MCAT --dry-run

        medanki generate -i chapter.pdf --vignettes -m 5
    """
    if ctx.invoked_subcommand is not None:
        return

    if input_path is None:
        console.print("[red]Error: Missing required option --input[/red]")
        raise typer.Exit(code=1)

    if not input_path.exists():
        console.print(f"[red]Error: Input path does not exist: {input_path}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[blue]Processing {input_path}...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        disable=not verbose,
    ) as progress:
        task = progress.add_task("Starting...", total=100)

        def on_progress(stage: str, pct: float):
            progress.update(task, completed=int(pct * 100), description=f"{stage}...")

        try:
            result = asyncio.run(
                process_document(
                    input_path=input_path,
                    exam=exam,
                    max_cards=max_cards,
                    enable_vignettes=vignettes,
                    on_progress=on_progress,
                )
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Hint: Set ANTHROPIC_API_KEY environment variable[/yellow]")
            raise typer.Exit(code=1) from None
        except Exception as e:
            console.print(f"[red]Error during processing: {e}[/red]")
            if verbose:
                import traceback
                console.print(traceback.format_exc())
            raise typer.Exit(code=1) from None

    cards = result.get("cards", [])
    stats = result.get("stats", {})

    table = Table(title="Generation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Cards", str(stats.get("total", 0)))
    table.add_row("Cloze Cards", str(stats.get("cloze", 0)))
    table.add_row("Vignette Cards", str(stats.get("vignette", 0)))
    table.add_row("Chunks Processed", str(stats.get("chunks", 0)))
    table.add_row("Duration", f"{stats.get('duration', 0):.2f}s")

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry run - no file created[/yellow]")
        if cards and verbose:
            console.print("\n[bold]Sample cards:[/bold]")
            for card in cards[:3]:
                text = getattr(card, "text", getattr(card, "front", "N/A"))
                console.print(f"  - {text[:80]}...")
        return

    if not cards:
        console.print("[yellow]No cards generated[/yellow]")
        return

    if output is None:
        output = Path.cwd() / f"{input_path.stem}_cards.apkg"

    create_apkg(cards, output, exam)
    console.print(f"\n[green]Created {output}[/green]")
