"""CLI commands for taxonomy database management."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

if TYPE_CHECKING:
    from medanki.storage.taxonomy_repository import TaxonomyRepository

app = typer.Typer(help="Browse, search, and manage medical taxonomy")
console = Console()

DEFAULT_DB_PATH = Path("data/taxonomy.db")


def get_repo(db_path: Path) -> TaxonomyRepository:
    """Get repository instance."""
    from medanki.storage.taxonomy_repository import TaxonomyRepository

    return TaxonomyRepository(db_path)


@app.command("build")
def build(
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        "-d",
        help="Database path",
    ),
    mcat_path: Path = typer.Option(
        Path("data/taxonomies/mcat.json"),
        "--mcat",
        help="MCAT taxonomy JSON",
    ),
    usmle_path: Path = typer.Option(
        Path("data/taxonomies/usmle_step1.json"),
        "--usmle",
        help="USMLE taxonomy JSON",
    ),
):
    """Build taxonomy database from JSON sources."""
    from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

    async def _build():
        db_path.parent.mkdir(parents=True, exist_ok=True)

        builder = TaxonomyDatabaseBuilder(db_path)
        await builder.initialize()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            if mcat_path.exists():
                progress.add_task("Loading MCAT taxonomy...", total=None)
                mcat_count = await builder.load_mcat_taxonomy(mcat_path)
                console.print(f"  Loaded {mcat_count} MCAT nodes")

            if usmle_path.exists():
                progress.add_task("Loading USMLE taxonomy...", total=None)
                usmle_count = await builder.load_usmle_taxonomy(usmle_path)
                console.print(f"  Loaded {usmle_count} USMLE nodes")

            progress.add_task("Building closure table...", total=None)
            edge_count = await builder.build_closure_table()
            console.print(f"  Created {edge_count} hierarchy edges")

        await builder.close()
        console.print(f"\n[green]Database built at {db_path}[/green]")

    asyncio.run(_build())


@app.command("enrich")
def enrich(
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        "-d",
        help="Database path",
    ),
    medmcqa_path: Path = typer.Option(
        Path("data/hf/medmcqa_topics.json"),
        "--medmcqa",
        help="MedMCQA topics JSON",
    ),
    anking_path: Path = typer.Option(
        Path("data/anking_tags.json"),
        "--anking",
        help="AnKing tags JSON",
    ),
    mesh_path: Path = typer.Option(
        Path("data/mesh_vocab.json"),
        "--mesh",
        help="MeSH vocabulary JSON",
    ),
):
    """Enrich database with additional sources."""
    from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

    async def _enrich():
        if not db_path.exists():
            console.print("[red]Database not found. Run 'build' first.[/red]")
            raise typer.Exit(code=1)

        builder = TaxonomyDatabaseBuilder(db_path)
        await builder.initialize()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            if medmcqa_path.exists():
                progress.add_task("Adding MedMCQA keywords...", total=None)
                count = await builder.enrich_from_medmcqa(medmcqa_path)
                console.print(f"  Added {count} MedMCQA keywords")

            if anking_path.exists():
                progress.add_task("Adding AnKing tags...", total=None)
                count = await builder.add_anking_tags(anking_path)
                console.print(f"  Added {count} AnKing tags")

            if mesh_path.exists():
                progress.add_task("Adding MeSH concepts...", total=None)
                count = await builder.add_mesh_concepts(mesh_path)
                console.print(f"  Added {count} MeSH concepts")

        await builder.close()
        console.print("\n[green]Enrichment complete[/green]")

    asyncio.run(_enrich())


@app.command("stats")
def stats(
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        "-d",
        help="Database path",
    ),
):
    """Print database statistics."""
    from scripts.build_taxonomy_db import TaxonomyDatabaseBuilder

    async def _stats():
        if not db_path.exists():
            console.print("[red]Database not found.[/red]")
            raise typer.Exit(code=1)

        builder = TaxonomyDatabaseBuilder(db_path)
        await builder.initialize()
        db_stats = await builder.get_stats()
        await builder.close()

        table = Table(title="Taxonomy Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        for key, value in db_stats.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        console.print(table)

    asyncio.run(_stats())


@app.command("list")
def list_topics(
    exam: str | None = typer.Option(
        None,
        "--exam",
        "-e",
        help="Filter by exam (MCAT, USMLE_STEP1)",
    ),
    node_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by node type",
    ),
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        "-d",
        help="Database path",
    ),
):
    """List taxonomy topics."""

    async def _list():
        if not db_path.exists():
            console.print("[red]Database not found. Run 'build' first.[/red]")
            raise typer.Exit(code=1)

        repo = get_repo(db_path)
        await repo.initialize()

        if exam and node_type:
            nodes = await repo.list_nodes_by_type(exam, node_type)
        elif exam:
            nodes = await repo.list_nodes_by_exam(exam)
        else:
            exams = await repo.list_exams()
            nodes = []
            for e in exams:
                nodes.extend(await repo.list_nodes_by_exam(e["id"]))

        await repo.close()

        table = Table(title="Taxonomy Topics")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Exam", style="magenta")

        for node in nodes[:50]:
            table.add_row(
                node["id"],
                node["title"][:50],
                node["node_type"],
                node["exam_id"],
            )

        if len(nodes) > 50:
            table.add_row("...", f"({len(nodes) - 50} more)", "", "")

        console.print(table)

    asyncio.run(_list())


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query (keyword)"),
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        "-d",
        help="Database path",
    ),
):
    """Search taxonomy by keyword."""

    async def _search():
        if not db_path.exists():
            console.print("[red]Database not found. Run 'build' first.[/red]")
            raise typer.Exit(code=1)

        repo = get_repo(db_path)
        await repo.initialize()
        results = await repo.search_nodes_by_keyword(query)
        await repo.close()

        if not results:
            console.print(f"[yellow]No topics found matching '{query}'[/yellow]")
            return

        table = Table(title=f"Search Results: '{query}'")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Exam", style="magenta")

        for node in results:
            table.add_row(
                node["id"],
                node["title"][:50],
                node["node_type"],
                node["exam_id"],
            )

        console.print(table)

    asyncio.run(_search())


@app.command("show")
def show(
    node_id: str = typer.Argument(..., help="Node ID to show"),
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        "-d",
        help="Database path",
    ),
):
    """Show details of a taxonomy node."""

    async def _show():
        if not db_path.exists():
            console.print("[red]Database not found. Run 'build' first.[/red]")
            raise typer.Exit(code=1)

        repo = get_repo(db_path)
        await repo.initialize()
        node = await repo.get_node(node_id)

        if not node:
            console.print(f"[red]Node not found: {node_id}[/red]")
            await repo.close()
            raise typer.Exit(code=1)

        path = await repo.get_path(node_id)
        keywords = await repo.get_keywords_for_node(node_id)
        children = await repo.get_children(node_id)
        await repo.close()

        console.print(f"\n[bold]{node['title']}[/bold]")
        console.print(f"ID: {node['id']}")
        console.print(f"Type: {node['node_type']}")
        console.print(f"Exam: {node['exam_id']}")
        if node.get("code"):
            console.print(f"Code: {node['code']}")

        console.print(f"\n[bold]Path:[/bold] {' > '.join(path)}")

        if keywords:
            console.print("\n[bold]Keywords:[/bold]")
            kw_list = [k["keyword"] for k in keywords[:10]]
            console.print(f"  {', '.join(kw_list)}")

        if children:
            console.print("\n[bold]Children:[/bold]")
            for child in children[:10]:
                console.print(f"  - {child['title']} ({child['id']})")
            if len(children) > 10:
                console.print(f"  ... and {len(children) - 10} more")

    asyncio.run(_show())


@app.command("tree")
def tree(
    node_id: str = typer.Argument(None, help="Root node ID (optional)"),
    depth: int = typer.Option(
        3,
        "--depth",
        "-d",
        help="Max depth to display",
    ),
    exam: str = typer.Option(
        None,
        "--exam",
        "-e",
        help="Filter by exam",
    ),
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db",
        help="Database path",
    ),
):
    """Display taxonomy as a tree."""

    async def _tree():
        if not db_path.exists():
            console.print("[red]Database not found. Run 'build' first.[/red]")
            raise typer.Exit(code=1)

        repo = get_repo(db_path)
        await repo.initialize()

        if node_id:
            node = await repo.get_node(node_id)
            if not node:
                console.print(f"[red]Node not found: {node_id}[/red]")
                await repo.close()
                raise typer.Exit(code=1)

            tree_widget = Tree(f"[bold]{node['title']}[/bold] ({node['id']})")
            descendants = await repo.get_descendants(node_id, max_depth=depth)

            node_map = {node_id: tree_widget}
            for desc in descendants:
                parent_key = desc.get("parent_id", node_id)
                parent_branch = node_map.get(parent_key, tree_widget)
                branch = parent_branch.add(f"{desc['title']} ({desc['id']})")
                node_map[desc["id"]] = branch

        else:
            exams_list = await repo.list_exams()
            if exam:
                exams_list = [e for e in exams_list if e["id"] == exam]

            tree_widget = Tree("[bold]Taxonomy[/bold]")

            for e in exams_list:
                exam_branch = tree_widget.add(f"[cyan]{e['name']}[/cyan] ({e['id']})")
                nodes = await repo.list_nodes_by_exam(e["id"])
                root_nodes = [n for n in nodes if not n.get("parent_id")]

                for root in root_nodes[:10]:
                    root_branch = exam_branch.add(f"[green]{root['title']}[/green] ({root['id']})")
                    children = await repo.get_descendants(root["id"], max_depth=depth - 1)
                    for child in children[:5]:
                        root_branch.add(f"{child['title']} ({child['id']})")
                    if len(children) > 5:
                        root_branch.add(f"... and {len(children) - 5} more")

                if len(root_nodes) > 10:
                    exam_branch.add(f"... and {len(root_nodes) - 10} more topics")

        await repo.close()
        console.print(tree_widget)

    asyncio.run(_tree())
