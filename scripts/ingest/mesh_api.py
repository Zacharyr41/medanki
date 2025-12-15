#!/usr/bin/env python3
"""MeSH API client for retrieving medical vocabulary from NIH."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
import typer

app = typer.Typer()


@dataclass
class MeshConcept:
    """A MeSH descriptor concept."""

    mesh_id: str
    name: str
    tree_numbers: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)


class MeshAPIClient:
    """Client for querying the MeSH API."""

    BASE_URL = "https://id.nlm.nih.gov/mesh"
    SPARQL_URL = "https://id.nlm.nih.gov/mesh/sparql"
    REQUEST_DELAY = 0.1

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "medanki" / "mesh"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time: float = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY)
        self._last_request_time = time.time()

    def _cache_key(self, query_type: str, query: str) -> str:
        """Generate a cache key for a query."""
        content = f"{query_type}:{query}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Any:
        """Retrieve cached result if available."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return None

    def _set_cached(self, cache_key: str, data: Any) -> None:
        """Store result in cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w") as f:
            json.dump(data, f)

    def search(self, query: str, limit: int = 20) -> list[MeshConcept]:
        """Search MeSH descriptors using SPARQL."""
        cache_key = self._cache_key("search", f"{query}:{limit}")
        cached = self._get_cached(cache_key)

        if cached is not None:
            return [
                MeshConcept(
                    mesh_id=c["mesh_id"],
                    name=c["name"],
                    tree_numbers=c["tree_numbers"],
                    synonyms=c["synonyms"],
                )
                for c in cached
            ]

        self._rate_limit()

        sparql_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

        SELECT ?d ?label ?treeNumber
        FROM <http://id.nlm.nih.gov/mesh>
        WHERE {{
            ?d a meshv:Descriptor .
            ?d rdfs:label ?label .
            ?d meshv:treeNumber ?treeNumber .
            FILTER(REGEX(?label, "{query}", "i"))
        }}
        LIMIT {limit}
        """

        response = requests.get(self.SPARQL_URL, params={"query": sparql_query, "format": "json"})
        response.raise_for_status()
        data = response.json()

        concepts_dict: dict[str, MeshConcept] = {}
        for binding in data["results"]["bindings"]:
            uri = binding["d"]["value"]
            mesh_id = uri.split("/")[-1]
            label = binding["label"]["value"]
            tree_number = binding["treeNumber"]["value"]

            if mesh_id not in concepts_dict:
                concepts_dict[mesh_id] = MeshConcept(
                    mesh_id=mesh_id,
                    name=label,
                    tree_numbers=[tree_number],
                    synonyms=[],
                )
            else:
                if tree_number not in concepts_dict[mesh_id].tree_numbers:
                    concepts_dict[mesh_id].tree_numbers.append(tree_number)

        results = list(concepts_dict.values())

        cache_data = [
            {
                "mesh_id": c.mesh_id,
                "name": c.name,
                "tree_numbers": c.tree_numbers,
                "synonyms": c.synonyms,
            }
            for c in results
        ]
        self._set_cached(cache_key, cache_data)

        return results

    def get_synonyms(self, term: str) -> list[str]:
        """Get synonyms for a MeSH term."""
        cache_key = self._cache_key("synonyms", term)
        cached = self._get_cached(cache_key)

        if cached is not None:
            return cached

        self._rate_limit()

        sparql_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT ?altLabel
        FROM <http://id.nlm.nih.gov/mesh>
        WHERE {{
            ?d a meshv:Descriptor .
            ?d rdfs:label ?label .
            ?d skos:altLabel ?altLabel .
            FILTER(REGEX(?label, "^{term}$", "i"))
        }}
        """

        response = requests.get(self.SPARQL_URL, params={"query": sparql_query, "format": "json"})
        response.raise_for_status()
        data = response.json()

        synonyms = []
        for binding in data["results"]["bindings"]:
            if "altLabel" in binding:
                synonyms.append(binding["altLabel"]["value"])

        self._set_cached(cache_key, synonyms)
        return synonyms

    def get_concept(self, descriptor_id: str) -> MeshConcept | None:
        """Get a specific MeSH concept by descriptor ID using REST API."""
        cache_key = self._cache_key("concept", descriptor_id)
        cached = self._get_cached(cache_key)

        if cached is not None:
            return MeshConcept(
                mesh_id=cached["mesh_id"],
                name=cached["name"],
                tree_numbers=cached["tree_numbers"],
                synonyms=cached["synonyms"],
            )

        self._rate_limit()

        url = f"{self.BASE_URL}/{descriptor_id}.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        label = data.get("label", {})
        name = label.get("@value", "") if isinstance(label, dict) else str(label)

        tree_numbers = []
        tree_data = data.get("treeNumber", [])
        if isinstance(tree_data, list):
            for t in tree_data:
                if isinstance(t, dict):
                    tree_numbers.append(t.get("@value", ""))
                else:
                    tree_numbers.append(str(t))
        elif isinstance(tree_data, dict):
            tree_numbers.append(tree_data.get("@value", ""))

        concept = MeshConcept(
            mesh_id=descriptor_id,
            name=name,
            tree_numbers=tree_numbers,
            synonyms=[],
        )

        cache_data = {
            "mesh_id": concept.mesh_id,
            "name": concept.name,
            "tree_numbers": concept.tree_numbers,
            "synonyms": concept.synonyms,
        }
        self._set_cached(cache_key, cache_data)

        return concept

    def get_category_descriptors(self, category: str, limit: int = 1000) -> list[MeshConcept]:
        """Get all descriptors in a MeSH category (e.g., 'C' for diseases)."""
        cache_key = self._cache_key("category", f"{category}:{limit}")
        cached = self._get_cached(cache_key)

        if cached is not None:
            return [
                MeshConcept(
                    mesh_id=c["mesh_id"],
                    name=c["name"],
                    tree_numbers=c["tree_numbers"],
                    synonyms=c["synonyms"],
                )
                for c in cached
            ]

        self._rate_limit()

        sparql_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

        SELECT ?d ?label ?treeNumber
        FROM <http://id.nlm.nih.gov/mesh>
        WHERE {{
            ?d a meshv:Descriptor .
            ?d rdfs:label ?label .
            ?d meshv:treeNumber ?treeNumber .
            FILTER(STRSTARTS(?treeNumber, "{category}"))
        }}
        LIMIT {limit}
        """

        response = requests.get(self.SPARQL_URL, params={"query": sparql_query, "format": "json"})
        response.raise_for_status()
        data = response.json()

        concepts_dict: dict[str, MeshConcept] = {}
        for binding in data["results"]["bindings"]:
            uri = binding["d"]["value"]
            mesh_id = uri.split("/")[-1]
            label = binding["label"]["value"]
            tree_number = binding["treeNumber"]["value"]

            if mesh_id not in concepts_dict:
                concepts_dict[mesh_id] = MeshConcept(
                    mesh_id=mesh_id,
                    name=label,
                    tree_numbers=[tree_number],
                    synonyms=[],
                )
            else:
                if tree_number not in concepts_dict[mesh_id].tree_numbers:
                    concepts_dict[mesh_id].tree_numbers.append(tree_number)

        results = list(concepts_dict.values())

        cache_data = [
            {
                "mesh_id": c.mesh_id,
                "name": c.name,
                "tree_numbers": c.tree_numbers,
                "synonyms": c.synonyms,
            }
            for c in results
        ]
        self._set_cached(cache_key, cache_data)

        return results

    def build_vocab(
        self, categories: list[str], output: Path, limit_per_category: int = 1000
    ) -> None:
        """Build a vocabulary JSON file from MeSH categories."""
        vocab: dict[str, dict] = {}

        for category in categories:
            descriptors = self.get_category_descriptors(category, limit=limit_per_category)
            for desc in descriptors:
                synonyms = self.get_synonyms(desc.name)
                vocab[desc.mesh_id] = {
                    "name": desc.name,
                    "tree_numbers": desc.tree_numbers,
                    "synonyms": synonyms,
                }

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(vocab, f, indent=2)


@app.command()
def search(query: str, limit: int = 20) -> None:
    """Search MeSH descriptors."""
    client = MeshAPIClient()
    results = client.search(query, limit=limit)
    for c in results:
        typer.echo(f"{c.mesh_id}: {c.name}")
        if c.tree_numbers:
            typer.echo(f"  Trees: {', '.join(c.tree_numbers)}")


@app.command()
def get_synonyms(term: str) -> None:
    """Get synonyms for a MeSH term."""
    client = MeshAPIClient()
    synonyms = client.get_synonyms(term)
    if synonyms:
        for s in synonyms:
            typer.echo(s)
    else:
        typer.echo("No synonyms found")


@app.command()
def get_concept(descriptor_id: str) -> None:
    """Get a specific MeSH concept by ID."""
    client = MeshAPIClient()
    concept = client.get_concept(descriptor_id)
    if concept:
        typer.echo(f"ID: {concept.mesh_id}")
        typer.echo(f"Name: {concept.name}")
        typer.echo(f"Trees: {', '.join(concept.tree_numbers)}")
    else:
        typer.echo("Concept not found")


@app.command()
def build_vocab(
    categories: str = "C,D",
    output: Path = Path("data/mesh_vocab.json"),
    limit: int = 1000,
) -> None:
    """Build vocabulary for specified MeSH categories."""
    category_list = [c.strip() for c in categories.split(",")]
    client = MeshAPIClient()
    client.build_vocab(category_list, output, limit_per_category=limit)
    typer.echo(f"Vocabulary saved to {output}")


if __name__ == "__main__":
    app()
