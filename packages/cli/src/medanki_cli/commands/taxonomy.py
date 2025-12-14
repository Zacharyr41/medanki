
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Browse and search medical taxonomy")
console = Console()


def get_topics(exam: str | None = None) -> list[dict]:
    topics = [
        {"id": "1", "name": "Cardiology", "exam": "USMLE"},
        {"id": "2", "name": "Neurology", "exam": "USMLE"},
        {"id": "3", "name": "Pulmonology", "exam": "USMLE"},
        {"id": "4", "name": "Osteopathic Principles", "exam": "COMLEX"},
    ]
    if exam:
        topics = [t for t in topics if t["exam"] == exam]
    return topics


def search_topics(query: str) -> list[dict]:
    all_topics = get_topics()
    return [t for t in all_topics if query.lower() in t["name"].lower()]


def get_topic_details(topic_id: str) -> dict | None:
    topics = {
        "1": {
            "id": "1",
            "name": "Cardiology",
            "exam": "USMLE",
            "subtopics": ["Heart Failure", "Arrhythmias", "Valvular Disease"],
        },
        "2": {
            "id": "2",
            "name": "Neurology",
            "exam": "USMLE",
            "subtopics": ["Stroke", "Epilepsy", "Movement Disorders"],
        },
    }
    return topics.get(topic_id)


@app.command("list")
def list_topics(
    exam: str | None = typer.Option(
        None,
        "--exam",
        "-e",
        help="Filter by exam type",
    ),
):
    topics = get_topics(exam=exam)

    table = Table(title="Medical Topics")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Exam", style="yellow")

    for topic in topics:
        table.add_row(topic["id"], topic["name"], topic["exam"])

    console.print(table)


@app.command("search")
def search(query: str = typer.Argument(..., help="Search query")):
    results = search_topics(query)

    if not results:
        console.print(f"[yellow]No topics found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}'")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Exam", style="yellow")

    for topic in results:
        table.add_row(topic["id"], topic["name"], topic["exam"])

    console.print(table)


@app.command("show")
def show(topic_id: str = typer.Argument(..., help="Topic ID to show")):
    details = get_topic_details(topic_id)

    if not details:
        console.print(f"[red]Topic not found: {topic_id}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{details['name']}[/bold]")
    console.print(f"ID: {details['id']}")
    console.print(f"Exam: {details['exam']}")
    console.print("\n[bold]Subtopics:[/bold]")
    for subtopic in details.get("subtopics", []):
        console.print(f"  - {subtopic}")
