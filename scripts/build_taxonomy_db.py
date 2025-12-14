#!/usr/bin/env python3
"""
Build taxonomy database from all sources.

Usage:
    python scripts/build_taxonomy_db.py build
    python scripts/build_taxonomy_db.py enrich
    python scripts/build_taxonomy_db.py stats
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core" / "src"))

from medanki.storage.taxonomy_repository import TaxonomyRepository

app = typer.Typer(help="Build and manage taxonomy database")
console = Console()


class TaxonomyDatabaseBuilder:
    """Builder for constructing taxonomy database from multiple sources."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._repo = TaxonomyRepository(db_path)

    async def initialize(self) -> None:
        """Initialize the database with schema."""
        await self._repo.initialize()

    async def close(self) -> None:
        """Close database connection."""
        await self._repo.close()

    async def load_mcat_taxonomy(self, json_path: Path) -> int:
        """Load MCAT taxonomy from JSON, returns node count."""
        data = json.loads(json_path.read_text())

        await self._repo.insert_exam({
            "id": "MCAT",
            "name": "Medical College Admission Test",
            "version": data.get("version", "2024"),
            "source_url": "https://aamc.org",
        })

        node_count = 0
        nodes = []
        keywords = []

        for fc in data.get("foundational_concepts", []):
            fc_id = f"MCAT_{fc['id']}"
            nodes.append({
                "id": fc_id,
                "exam_id": "MCAT",
                "node_type": "foundational_concept",
                "code": fc["id"],
                "title": fc["title"],
                "sort_order": node_count,
            })

            for kw in fc.get("keywords", []):
                keywords.append({
                    "node_id": fc_id,
                    "keyword": kw,
                    "keyword_type": "general",
                    "source": "mcat_taxonomy",
                })

            node_count += 1

            for cat in fc.get("categories", []):
                cat_id = f"MCAT_{cat['id']}"
                nodes.append({
                    "id": cat_id,
                    "exam_id": "MCAT",
                    "node_type": "content_category",
                    "code": cat["id"],
                    "title": cat["title"],
                    "parent_id": fc_id,
                    "sort_order": node_count,
                })

                for kw in cat.get("keywords", []):
                    keywords.append({
                        "node_id": cat_id,
                        "keyword": kw,
                        "keyword_type": "general",
                        "source": "mcat_taxonomy",
                    })

                node_count += 1

        await self._repo.bulk_insert_nodes(nodes)
        if keywords:
            await self._repo.bulk_insert_keywords(keywords)

        return len(nodes)

    async def load_usmle_taxonomy(self, json_path: Path) -> int:
        """Load USMLE taxonomy from JSON, returns node count."""
        data = json.loads(json_path.read_text())

        await self._repo.insert_exam({
            "id": "USMLE_STEP1",
            "name": "USMLE Step 1",
            "version": data.get("version", "2024"),
            "source_url": "https://usmle.org",
        })

        node_count = 0
        nodes = []
        keywords = []

        for system in data.get("systems", []):
            system_id = f"USMLE_{system['id']}"
            nodes.append({
                "id": system_id,
                "exam_id": "USMLE_STEP1",
                "node_type": "organ_system",
                "code": system["id"],
                "title": system["title"],
                "sort_order": node_count,
            })

            for kw in system.get("keywords", []):
                keywords.append({
                    "node_id": system_id,
                    "keyword": kw,
                    "keyword_type": "general",
                    "source": "usmle_taxonomy",
                })

            node_count += 1

            for topic in system.get("topics", []):
                topic_id = f"USMLE_{topic['id']}"
                nodes.append({
                    "id": topic_id,
                    "exam_id": "USMLE_STEP1",
                    "node_type": "topic",
                    "code": topic["id"],
                    "title": topic["title"],
                    "parent_id": system_id,
                    "sort_order": node_count,
                })

                for kw in topic.get("keywords", []):
                    keywords.append({
                        "node_id": topic_id,
                        "keyword": kw,
                        "keyword_type": "general",
                        "source": "usmle_taxonomy",
                    })

                node_count += 1

        await self._repo.bulk_insert_nodes(nodes)
        if keywords:
            await self._repo.bulk_insert_keywords(keywords)

        return len(nodes)

    async def build_closure_table(self) -> int:
        """Build closure table for hierarchy queries, returns edge count."""
        return await self._repo.build_closure_table()

    async def enrich_from_medmcqa(self, topics_path: Path) -> int:
        """Add MedMCQA keywords to matching nodes, returns count."""
        if not topics_path.exists():
            return 0

        data = json.loads(topics_path.read_text())
        count = 0

        for topic in data.get("topics", []):
            for kw in topic.get("keywords", []):
                nodes = await self._repo.search_nodes_by_keyword(kw)
                for node in nodes:
                    try:
                        await self._repo.insert_keyword({
                            "node_id": node["id"],
                            "keyword": f"medmcqa:{topic['name']}",
                            "keyword_type": "medmcqa",
                            "source": "medmcqa",
                        })
                        count += 1
                    except Exception:
                        pass

        return count

    async def add_anking_tags(self, tags_path: Path) -> int:
        """Import AnKing tag mappings, returns count."""
        if not tags_path.exists():
            return 0

        data = json.loads(tags_path.read_text())
        conn = await self._repo._get_connection()
        count = 0

        for tag in data.get("tags", []):
            try:
                await conn.execute(
                    """INSERT INTO anking_tags (tag_path, note_count)
                       VALUES (?, ?)""",
                    (tag["path"], tag.get("count", 0)),
                )
                count += 1
            except Exception:
                pass

        await conn.commit()
        return count

    async def add_mesh_concepts(self, vocab_path: Path) -> int:
        """Add MeSH vocabulary concepts, returns count."""
        if not vocab_path.exists():
            return 0

        data = json.loads(vocab_path.read_text())
        conn = await self._repo._get_connection()
        count = 0

        for concept in data.get("concepts", []):
            try:
                await conn.execute(
                    """INSERT INTO mesh_concepts (mesh_id, name, synonyms)
                       VALUES (?, ?, ?)""",
                    (
                        concept["mesh_id"],
                        concept["name"],
                        json.dumps(concept.get("synonyms", [])),
                    ),
                )
                count += 1
            except Exception:
                pass

        await conn.commit()
        return count

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        conn = await self._repo._get_connection()

        stats = {}

        cursor = await conn.execute("SELECT COUNT(*) FROM exams")
        row = await cursor.fetchone()
        stats["exams"] = row[0] if row else 0

        cursor = await conn.execute("SELECT COUNT(*) FROM taxonomy_nodes")
        row = await cursor.fetchone()
        stats["nodes"] = row[0] if row else 0

        cursor = await conn.execute("SELECT COUNT(*) FROM taxonomy_edges")
        row = await cursor.fetchone()
        stats["edges"] = row[0] if row else 0

        cursor = await conn.execute("SELECT COUNT(*) FROM keywords")
        row = await cursor.fetchone()
        stats["keywords"] = row[0] if row else 0

        cursor = await conn.execute("SELECT COUNT(*) FROM anking_tags")
        row = await cursor.fetchone()
        stats["anking_tags"] = row[0] if row else 0

        cursor = await conn.execute("SELECT COUNT(*) FROM mesh_concepts")
        row = await cursor.fetchone()
        stats["mesh_concepts"] = row[0] if row else 0

        return stats


@app.command()
def build(
    db_path: Path = typer.Option(
        Path("data/taxonomy.db"),
        "--db",
        "-d",
        help="Database path",
    ),
    mcat_path: Path = typer.Option(
        Path("data/taxonomies/mcat.json"),
        "--mcat",
        help="MCAT taxonomy JSON path",
    ),
    usmle_path: Path = typer.Option(
        Path("data/taxonomies/usmle_step1.json"),
        "--usmle",
        help="USMLE taxonomy JSON path",
    ),
):
    """Build taxonomy database from JSON sources."""
    import asyncio

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


@app.command()
def enrich(
    db_path: Path = typer.Option(
        Path("data/taxonomy.db"),
        "--db",
        "-d",
        help="Database path",
    ),
    medmcqa_path: Path = typer.Option(
        Path("data/hf/medmcqa_topics.json"),
        "--medmcqa",
        help="MedMCQA topics JSON path",
    ),
    anking_path: Path = typer.Option(
        Path("data/anking_tags.json"),
        "--anking",
        help="AnKing tags JSON path",
    ),
    mesh_path: Path = typer.Option(
        Path("data/mesh_vocab.json"),
        "--mesh",
        help="MeSH vocabulary JSON path",
    ),
):
    """Enrich database with additional sources."""
    import asyncio

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


@app.command()
def stats(
    db_path: Path = typer.Option(
        Path("data/taxonomy.db"),
        "--db",
        "-d",
        help="Database path",
    ),
):
    """Print database statistics."""
    import asyncio

    async def _stats():
        if not db_path.exists():
            console.print("[red]Database not found.[/red]")
            raise typer.Exit(code=1)

        builder = TaxonomyDatabaseBuilder(db_path)
        await builder.initialize()
        stats = await builder.get_stats()
        await builder.close()

        table = Table(title="Taxonomy Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        for key, value in stats.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        console.print(table)

    asyncio.run(_stats())


if __name__ == "__main__":
    app()
