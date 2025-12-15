"""Taxonomy repository for MCAT and USMLE classification data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite


class TaxonomyRepository:
    """Repository for taxonomy data with closure table hierarchy support."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    async def initialize(self) -> None:
        conn = await self._get_connection()
        schema_path = Path(__file__).parent / "taxonomy_schema.sql"
        await conn.executescript(schema_path.read_text())
        await conn.commit()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def get_tables(self) -> list[str]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def insert_exam(self, exam: dict[str, Any]) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """INSERT INTO exams (id, name, version, source_url, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                exam["id"],
                exam["name"],
                exam.get("version"),
                exam.get("source_url"),
                datetime.utcnow().isoformat(),
            ),
        )
        await conn.commit()
        return exam["id"]

    async def get_exam(self, exam_id: str) -> dict[str, Any] | None:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_exams(self) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM exams ORDER BY name")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def insert_node(self, node: dict[str, Any]) -> str:
        conn = await self._get_connection()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            """INSERT INTO taxonomy_nodes
               (id, exam_id, node_type, code, title, description,
                percentage_min, percentage_max, parent_id, sort_order, metadata,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node["id"],
                node["exam_id"],
                node["node_type"],
                node.get("code"),
                node["title"],
                node.get("description"),
                node.get("percentage_min"),
                node.get("percentage_max"),
                node.get("parent_id"),
                node.get("sort_order", 0),
                json.dumps(node.get("metadata")) if node.get("metadata") else None,
                now,
                now,
            ),
        )
        await conn.commit()
        return node["id"]

    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT * FROM taxonomy_nodes WHERE id = ?", (node_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        result = dict(row)
        if result.get("metadata"):
            result["metadata"] = json.loads(result["metadata"])
        return result

    async def update_node(self, node_id: str, updates: dict[str, Any]) -> bool:
        conn = await self._get_connection()
        allowed_fields = {
            "title",
            "description",
            "code",
            "percentage_min",
            "percentage_max",
            "parent_id",
            "sort_order",
            "metadata",
        }
        fields = []
        values = []
        for key, value in updates.items():
            if key in allowed_fields:
                fields.append(f"{key} = ?")
                if key == "metadata" and value is not None:
                    value = json.dumps(value)
                values.append(value)

        if not fields:
            return False

        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(node_id)

        await conn.execute(f"UPDATE taxonomy_nodes SET {', '.join(fields)} WHERE id = ?", values)
        await conn.commit()
        return True

    async def delete_node(self, node_id: str) -> bool:
        conn = await self._get_connection()
        cursor = await conn.execute("DELETE FROM taxonomy_nodes WHERE id = ?", (node_id,))
        await conn.commit()
        return cursor.rowcount > 0

    async def list_nodes_by_exam(self, exam_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM taxonomy_nodes WHERE exam_id = ? ORDER BY sort_order",
            (exam_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def list_nodes_by_type(self, exam_id: str, node_type: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT * FROM taxonomy_nodes
               WHERE exam_id = ? AND node_type = ?
               ORDER BY sort_order""",
            (exam_id, node_type),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def bulk_insert_nodes(self, nodes: list[dict[str, Any]]) -> int:
        conn = await self._get_connection()
        now = datetime.utcnow().isoformat()
        data = [
            (
                n["id"],
                n["exam_id"],
                n["node_type"],
                n.get("code"),
                n["title"],
                n.get("description"),
                n.get("percentage_min"),
                n.get("percentage_max"),
                n.get("parent_id"),
                n.get("sort_order", 0),
                json.dumps(n.get("metadata")) if n.get("metadata") else None,
                now,
                now,
            )
            for n in nodes
        ]
        await conn.executemany(
            """INSERT INTO taxonomy_nodes
               (id, exam_id, node_type, code, title, description,
                percentage_min, percentage_max, parent_id, sort_order, metadata,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data,
        )
        await conn.commit()
        return len(nodes)

    async def build_closure_table(self) -> int:
        conn = await self._get_connection()
        await conn.execute("DELETE FROM taxonomy_edges")
        await conn.execute(
            """INSERT INTO taxonomy_edges (ancestor_id, descendant_id, depth)
               SELECT id, id, 0 FROM taxonomy_nodes"""
        )

        depth = 1
        while True:
            cursor = await conn.execute(
                """INSERT OR IGNORE INTO taxonomy_edges (ancestor_id, descendant_id, depth)
                   SELECT e.ancestor_id, n.id, e.depth + 1
                   FROM taxonomy_edges e
                   JOIN taxonomy_nodes n ON n.parent_id = e.descendant_id
                   WHERE e.depth = ?""",
                (depth - 1,),
            )

            if cursor.rowcount == 0:
                break
            depth += 1

        await conn.commit()
        cursor = await conn.execute("SELECT COUNT(*) FROM taxonomy_edges")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_ancestors(self, node_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT n.* FROM taxonomy_nodes n
               JOIN taxonomy_edges e ON n.id = e.ancestor_id
               WHERE e.descendant_id = ? AND e.depth > 0
               ORDER BY e.depth DESC""",
            (node_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_descendants(
        self, node_id: str, max_depth: int | None = None
    ) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        sql = """SELECT n.*, e.depth FROM taxonomy_nodes n
                 JOIN taxonomy_edges e ON n.id = e.descendant_id
                 WHERE e.ancestor_id = ? AND e.depth > 0"""
        params: list[Any] = [node_id]
        if max_depth is not None:
            sql += " AND e.depth <= ?"
            params.append(max_depth)
        sql += " ORDER BY e.depth, n.sort_order"

        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_children(self, node_id: str) -> list[dict[str, Any]]:
        return await self.get_descendants(node_id, max_depth=1)

    async def get_path(self, node_id: str) -> list[str]:
        ancestors = await self.get_ancestors(node_id)
        node = await self.get_node(node_id)
        if node is None:
            return []
        return [a["title"] for a in ancestors] + [node["title"]]

    async def insert_keyword(self, keyword: dict[str, Any]) -> int:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """INSERT INTO keywords (node_id, keyword, keyword_type, weight, source)
               VALUES (?, ?, ?, ?, ?)""",
            (
                keyword["node_id"],
                keyword["keyword"],
                keyword.get("keyword_type", "general"),
                keyword.get("weight", 1.0),
                keyword.get("source"),
            ),
        )
        await conn.commit()
        return cursor.lastrowid or 0

    async def get_keywords_for_node(self, node_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM keywords WHERE node_id = ? ORDER BY weight DESC", (node_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def bulk_insert_keywords(self, keywords: list[dict[str, Any]]) -> int:
        conn = await self._get_connection()
        data = [
            (
                k["node_id"],
                k["keyword"],
                k.get("keyword_type", "general"),
                k.get("weight", 1.0),
                k.get("source"),
            )
            for k in keywords
        ]
        await conn.executemany(
            """INSERT INTO keywords (node_id, keyword, keyword_type, weight, source)
               VALUES (?, ?, ?, ?, ?)""",
            data,
        )
        await conn.commit()
        return len(keywords)

    async def search_nodes_by_keyword(self, keyword: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT DISTINCT n.* FROM taxonomy_nodes n
               JOIN keywords k ON n.id = k.node_id
               WHERE k.keyword = ?""",
            (keyword,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def add_cross_classification(self, cc: dict[str, Any]) -> int:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """INSERT INTO cross_classifications
               (primary_node_id, secondary_node_id, relationship_type, weight)
               VALUES (?, ?, ?, ?)""",
            (
                cc["primary_node_id"],
                cc["secondary_node_id"],
                cc["relationship_type"],
                cc.get("weight", 1.0),
            ),
        )
        await conn.commit()
        return cursor.lastrowid or 0

    async def get_cross_classifications(self, node_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT * FROM cross_classifications WHERE primary_node_id = ?", (node_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def insert_resource(self, resource: dict[str, Any]) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """INSERT INTO resources
               (id, name, resource_type, version, anking_tag_prefix, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                resource["id"],
                resource["name"],
                resource["resource_type"],
                resource.get("version"),
                resource.get("anking_tag_prefix"),
                json.dumps(resource.get("metadata")) if resource.get("metadata") else None,
            ),
        )
        await conn.commit()
        return resource["id"]

    async def insert_resource_section(self, section: dict[str, Any]) -> str:
        conn = await self._get_connection()
        await conn.execute(
            """INSERT INTO resource_sections
               (id, resource_id, title, section_type, code, parent_id,
                page_start, page_end, duration_seconds, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                section["id"],
                section["resource_id"],
                section["title"],
                section.get("section_type"),
                section.get("code"),
                section.get("parent_id"),
                section.get("page_start"),
                section.get("page_end"),
                section.get("duration_seconds"),
                section.get("sort_order", 0),
            ),
        )
        await conn.commit()
        return section["id"]

    async def add_resource_mapping(self, mapping: dict[str, Any]) -> int:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """INSERT INTO resource_mappings
               (node_id, section_id, relevance_score, is_primary)
               VALUES (?, ?, ?, ?)""",
            (
                mapping["node_id"],
                mapping["section_id"],
                mapping.get("relevance_score", 1.0),
                mapping.get("is_primary", False),
            ),
        )
        await conn.commit()
        return cursor.lastrowid or 0

    async def get_resources_for_node(self, node_id: str) -> list[dict[str, Any]]:
        conn = await self._get_connection()
        cursor = await conn.execute(
            """SELECT rm.*, rs.title as section_title, r.name as resource_name
               FROM resource_mappings rm
               JOIN resource_sections rs ON rm.section_id = rs.id
               JOIN resources r ON rs.resource_id = r.id
               WHERE rm.node_id = ?""",
            (node_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
