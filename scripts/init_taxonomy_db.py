#!/usr/bin/env python3
"""Initialize taxonomy SQLite database from JSON files."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core" / "src"))

from medanki.storage.taxonomy_repository import TaxonomyRepository


async def load_mcat_taxonomy(repo: TaxonomyRepository, json_path: Path) -> int:
    """Load MCAT taxonomy from JSON."""
    with open(json_path) as f:
        data = json.load(f)

    await repo.insert_exam({
        "id": "MCAT",
        "name": "Medical College Admission Test",
        "version": data.get("version", "2024"),
        "source_url": "https://aamc.org",
    })

    nodes = []
    keywords = []
    sort_order = 0

    for fc in data.get("foundational_concepts", []):
        fc_id = f"MCAT_{fc['id']}"
        nodes.append({
            "id": fc_id,
            "exam_id": "MCAT",
            "node_type": "foundational_concept",
            "code": fc["id"],
            "title": fc["title"],
            "parent_id": None,
            "sort_order": sort_order,
        })
        sort_order += 1

        for kw in fc.get("keywords", []):
            keywords.append({"node_id": fc_id, "keyword": kw.lower()})

        for cat in fc.get("categories", []):
            cat_id = f"MCAT_{cat['id']}"
            nodes.append({
                "id": cat_id,
                "exam_id": "MCAT",
                "node_type": "content_category",
                "code": cat["id"],
                "title": cat["title"],
                "parent_id": fc_id,
                "sort_order": sort_order,
            })
            sort_order += 1

            for kw in cat.get("keywords", []):
                keywords.append({"node_id": cat_id, "keyword": kw.lower()})

    await repo.bulk_insert_nodes(nodes)
    if keywords:
        await repo.bulk_insert_keywords(keywords)

    return len(nodes)


async def load_usmle_taxonomy(repo: TaxonomyRepository, json_path: Path) -> int:
    """Load USMLE taxonomy from JSON."""
    with open(json_path) as f:
        data = json.load(f)

    await repo.insert_exam({
        "id": "USMLE_STEP1",
        "name": "United States Medical Licensing Examination Step 1",
        "version": data.get("version", "2024"),
        "source_url": "https://nbme.org",
    })

    nodes = []
    keywords = []
    sort_order = 0

    for sys in data.get("systems", []):
        sys_id = f"USMLE_{sys['id']}"
        nodes.append({
            "id": sys_id,
            "exam_id": "USMLE_STEP1",
            "node_type": "organ_system",
            "code": sys["id"],
            "title": sys["title"],
            "parent_id": None,
            "sort_order": sort_order,
        })
        sort_order += 1

        for kw in sys.get("keywords", []):
            keywords.append({"node_id": sys_id, "keyword": kw.lower()})

        for topic in sys.get("topics", []):
            topic_id = f"USMLE_{topic['id']}"
            nodes.append({
                "id": topic_id,
                "exam_id": "USMLE_STEP1",
                "node_type": "topic",
                "code": topic["id"],
                "title": topic["title"],
                "parent_id": sys_id,
                "sort_order": sort_order,
            })
            sort_order += 1

            for kw in topic.get("keywords", []):
                keywords.append({"node_id": topic_id, "keyword": kw.lower()})

    await repo.bulk_insert_nodes(nodes)
    if keywords:
        await repo.bulk_insert_keywords(keywords)

    return len(nodes)


async def main():
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "taxonomy.db"
    mcat_json = project_root / "data" / "taxonomies" / "mcat.json"
    usmle_json = project_root / "data" / "taxonomies" / "usmle_step1.json"

    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database: {db_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    repo = TaxonomyRepository(db_path)

    try:
        print("Initializing database schema...")
        await repo.initialize()

        mcat_count = 0
        usmle_count = 0

        if mcat_json.exists():
            print(f"Loading MCAT taxonomy from {mcat_json}...")
            mcat_count = await load_mcat_taxonomy(repo, mcat_json)
            print(f"  Loaded {mcat_count} MCAT nodes")
        else:
            print(f"Warning: MCAT JSON not found at {mcat_json}")

        if usmle_json.exists():
            print(f"Loading USMLE taxonomy from {usmle_json}...")
            usmle_count = await load_usmle_taxonomy(repo, usmle_json)
            print(f"  Loaded {usmle_count} USMLE nodes")
        else:
            print(f"Warning: USMLE JSON not found at {usmle_json}")

        print("Building closure table for hierarchy queries...")
        edge_count = await repo.build_closure_table()
        print(f"  Created {edge_count} edges")

        tables = await repo.get_tables()
        print(f"\nDatabase created with tables: {', '.join(tables)}")
        print(f"Total nodes: {mcat_count + usmle_count}")
        print(f"Database path: {db_path}")

    finally:
        await repo.close()


if __name__ == "__main__":
    asyncio.run(main())
