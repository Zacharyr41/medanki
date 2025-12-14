#!/usr/bin/env python3
"""Fetch AnKing data sources: deck export and resource mapping sheets."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer

app = typer.Typer(help="Fetch AnKing data sources")

ANKING_REPO_URL = "https://github.com/langfield/AnKing-v11.git"
DEFAULT_DATA_DIR = Path("data/source/anking")

RESOURCE_SHEETS = {
    "boards_beyond": "https://docs.google.com/spreadsheets/d/1Wm41IYA7ty8o-c8en73YcsnBitMoIJBqOoivP46xPag/export?format=csv",
    "pathoma": "https://docs.google.com/spreadsheets/d/1NAeezYHHN5qXgC7AmfHF6CiWdOFn3YAh7ixa56eD64c/export?format=csv",
    "sketchy": "https://docs.google.com/spreadsheets/d/1tPFMKQ6lCDuS8vgn8HTWKh3omDXrUHzCvmoFzogr2CQ/export?format=csv",
}


def clone_anking_repo(target_dir: Path, shallow: bool = True) -> bool:
    target_path = target_dir / "AnKing-v11"

    if target_path.exists():
        typer.echo(f"AnKing repo already exists at {target_path}")
        return True

    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["git", "clone"]
    if shallow:
        cmd.extend(["--depth", "1"])
    cmd.extend([ANKING_REPO_URL, str(target_path)])

    typer.echo(f"Cloning AnKing-v11 to {target_path}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        typer.echo(f"Clone failed: {result.stderr}", err=True)
        return False

    typer.echo("Clone successful!")
    return True


def fetch_resource_sheets(target_dir: Path) -> dict[str, bool]:
    try:
        import pandas as pd
    except ImportError:
        typer.echo("pandas not installed, skipping sheet downloads", err=True)
        return dict.fromkeys(RESOURCE_SHEETS, False)

    target_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for name, url in RESOURCE_SHEETS.items():
        output_path = target_dir / f"{name}.csv"
        typer.echo(f"Fetching {name} sheet...")

        try:
            df = pd.read_csv(url)
            df.to_csv(output_path, index=False)
            typer.echo(f"  Saved {len(df)} rows to {output_path}")
            results[name] = True
        except Exception as e:
            typer.echo(f"  Failed: {e}", err=True)
            results[name] = False

    return results


@app.command()
def fetch_all(
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        help="Base directory for downloaded data",
    ),
    skip_repo: bool = typer.Option(
        False,
        help="Skip cloning the AnKing repository",
    ),
    skip_sheets: bool = typer.Option(
        False,
        help="Skip downloading resource mapping sheets",
    ),
) -> None:
    """Fetch all AnKing data sources."""
    typer.echo("=" * 50)
    typer.echo("Fetching AnKing Data Sources")
    typer.echo("=" * 50)

    if not skip_repo:
        clone_anking_repo(data_dir)
    else:
        typer.echo("Skipping repo clone")

    if not skip_sheets:
        sheets_dir = data_dir / "sheets"
        fetch_resource_sheets(sheets_dir)
    else:
        typer.echo("Skipping sheet downloads")

    typer.echo("=" * 50)
    typer.echo("Done!")


@app.command()
def clone(
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        help="Base directory for the repository",
    ),
    full: bool = typer.Option(
        False,
        help="Clone full history (not shallow)",
    ),
) -> None:
    """Clone the AnKing-v11 repository."""
    clone_anking_repo(data_dir, shallow=not full)


@app.command()
def sheets(
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR / "sheets",
        help="Directory to save CSV files",
    ),
) -> None:
    """Download resource mapping sheets."""
    fetch_resource_sheets(data_dir)


if __name__ == "__main__":
    app()
