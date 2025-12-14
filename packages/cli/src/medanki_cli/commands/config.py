from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage MedAnki configuration")
console = Console()


_config: dict = {
    "output_dir": str(Path.home() / "medanki"),
    "default_exam": "USMLE",
    "verbose": False,
}


def get_config() -> dict:
    return _config.copy()


def set_config(key: str, value: str) -> bool:
    if key in _config:
        if key == "verbose":
            _config[key] = value.lower() in ("true", "1", "yes")
        else:
            _config[key] = value
        return True
    return False


def get_config_path() -> Path:
    return Path.home() / ".config" / "medanki" / "config.toml"


@app.command("show")
def show():
    config = get_config()

    table = Table(title="MedAnki Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in config.items():
        table.add_row(key, str(value))

    console.print(table)


@app.command("set")
def set_value(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    success = set_config(key, value)

    if success:
        console.print(f"[green]Set {key} = {value}[/green]")
    else:
        console.print(f"[red]Unknown configuration key: {key}[/red]")
        raise typer.Exit(code=1)


@app.command("path")
def path():
    config_path = get_config_path()
    console.print(f"Config file: {config_path}")
