"""Enhanced taxonomy service with SQLite backend."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from medanki.models.enums import ExamType
from medanki.models.taxonomy import NodeType, TaxonomyNode
from medanki.storage.taxonomy_repository import TaxonomyRepository


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Protocol for vector store implementations."""

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        ...


class TaxonomyServiceV2:
    """Enhanced taxonomy service with SQLite backend and closure table hierarchy."""

    def __init__(self, db_path: Path | str, vector_store: VectorStoreProtocol | None = None):
        self._db_path = Path(db_path)
        self._repo: TaxonomyRepository | None = None
        self._vector_store = vector_store

    async def _get_repo(self) -> TaxonomyRepository:
        """Get or create repository connection."""
        if self._repo is None:
            self._repo = TaxonomyRepository(self._db_path)
        return self._repo

    async def close(self) -> None:
        """Close database connection."""
        if self._repo is not None:
            await self._repo.close()
            self._repo = None

    async def __aenter__(self) -> TaxonomyServiceV2:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def _row_to_node(self, row: dict[str, Any], keywords: list[str] | None = None) -> TaxonomyNode:
        """Convert database row to TaxonomyNode."""
        node_type_str = row.get("node_type", "topic")
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            node_type = NodeType.TOPIC

        return TaxonomyNode(
            id=row["id"],
            exam_id=row["exam_id"],
            node_type=node_type,
            code=row.get("code"),
            title=row["title"],
            description=row.get("description"),
            percentage_min=row.get("percentage_min"),
            percentage_max=row.get("percentage_max"),
            parent_id=row.get("parent_id"),
            sort_order=row.get("sort_order", 0),
            metadata=row.get("metadata"),
            keywords=keywords or [],
            depth=row.get("depth"),
        )

    async def get_node(self, node_id: str) -> TaxonomyNode | None:
        """Get a taxonomy node by ID with associated keywords."""
        repo = await self._get_repo()
        row = await repo.get_node(node_id)
        if row is None:
            return None

        keywords_data = await repo.get_keywords_for_node(node_id)
        keywords = [k["keyword"] for k in keywords_data]

        return self._row_to_node(row, keywords)

    async def get_nodes_by_exam(self, exam: ExamType) -> list[TaxonomyNode]:
        """Get all nodes for a specific exam."""
        repo = await self._get_repo()
        exam_id = self._exam_type_to_id(exam)
        rows = await repo.list_nodes_by_exam(exam_id)

        nodes = []
        for row in rows:
            keywords_data = await repo.get_keywords_for_node(row["id"])
            keywords = [k["keyword"] for k in keywords_data]
            nodes.append(self._row_to_node(row, keywords))

        return nodes

    async def get_root_nodes(self, exam: ExamType) -> list[TaxonomyNode]:
        """Get root nodes (no parent) for an exam."""
        repo = await self._get_repo()
        exam_id = self._exam_type_to_id(exam)
        rows = await repo.list_nodes_by_exam(exam_id)

        roots = []
        for row in rows:
            if row.get("parent_id") is None:
                keywords_data = await repo.get_keywords_for_node(row["id"])
                keywords = [k["keyword"] for k in keywords_data]
                roots.append(self._row_to_node(row, keywords))

        return roots

    async def get_ancestors(self, node_id: str) -> list[TaxonomyNode]:
        """Get all ancestors of a node, ordered from root to immediate parent."""
        repo = await self._get_repo()
        rows = await repo.get_ancestors(node_id)

        nodes = []
        for row in rows:
            keywords_data = await repo.get_keywords_for_node(row["id"])
            keywords = [k["keyword"] for k in keywords_data]
            nodes.append(self._row_to_node(row, keywords))

        return nodes

    async def get_descendants(
        self, node_id: str, max_depth: int | None = None
    ) -> list[TaxonomyNode]:
        """Get all descendants of a node, optionally limited by depth."""
        repo = await self._get_repo()
        rows = await repo.get_descendants(node_id, max_depth)

        nodes = []
        for row in rows:
            keywords_data = await repo.get_keywords_for_node(row["id"])
            keywords = [k["keyword"] for k in keywords_data]
            nodes.append(self._row_to_node(row, keywords))

        return nodes

    async def get_children(self, node_id: str) -> list[TaxonomyNode]:
        """Get direct children of a node."""
        repo = await self._get_repo()
        rows = await repo.get_children(node_id)

        nodes = []
        for row in rows:
            keywords_data = await repo.get_keywords_for_node(row["id"])
            keywords = [k["keyword"] for k in keywords_data]
            nodes.append(self._row_to_node(row, keywords))

        return nodes

    async def get_path(self, node_id: str) -> str:
        """Get the full hierarchical path of a node as a string."""
        repo = await self._get_repo()
        path_parts = await repo.get_path(node_id)
        if not path_parts:
            return ""
        return " > ".join(path_parts)

    async def search_by_keyword(
        self, keyword: str, exam: ExamType | None = None
    ) -> list[TaxonomyNode]:
        """Search nodes by keyword with optional exam filter."""
        repo = await self._get_repo()
        keyword_lower = keyword.lower()

        nodes_by_keyword = await repo.search_nodes_by_keyword(keyword_lower)

        if exam is not None:
            exam_id = self._exam_type_to_id(exam)
            rows = await repo.list_nodes_by_exam(exam_id)
        else:
            rows = []
            for exam_type in [ExamType.MCAT, ExamType.USMLE_STEP1]:
                exam_id = self._exam_type_to_id(exam_type)
                rows.extend(await repo.list_nodes_by_exam(exam_id))

        title_matches = [row for row in rows if keyword_lower in row["title"].lower()]

        seen_ids = set()
        result_nodes = []

        for row in nodes_by_keyword:
            if exam is not None:
                exam_id = self._exam_type_to_id(exam)
                if row["exam_id"] != exam_id:
                    continue
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                keywords_data = await repo.get_keywords_for_node(row["id"])
                keywords = [k["keyword"] for k in keywords_data]
                result_nodes.append(self._row_to_node(row, keywords))

        for row in title_matches:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                keywords_data = await repo.get_keywords_for_node(row["id"])
                keywords = [k["keyword"] for k in keywords_data]
                result_nodes.append(self._row_to_node(row, keywords))

        return result_nodes

    async def semantic_search(
        self, query: str, limit: int = 10
    ) -> list[tuple[TaxonomyNode, float]]:
        """Search nodes using semantic similarity via vector store."""
        if self._vector_store is None:
            return []

        results = await self._vector_store.search(query, limit)

        nodes_with_scores = []
        for result in results:
            node_id = result.get("node_id")
            score = result.get("score", 0.0)
            if node_id:
                node = await self.get_node(node_id)
                if node:
                    nodes_with_scores.append((node, score))

        return nodes_with_scores

    async def get_topics_by_system_and_discipline(
        self, system_id: str, discipline_id: str
    ) -> list[TaxonomyNode]:
        """Get topics at the intersection of a system and discipline (USMLE)."""
        repo = await self._get_repo()

        system_descendants = await repo.get_descendants(system_id)
        system_node_ids = {system_id} | {d["id"] for d in system_descendants}

        result_nodes = []
        for node_id in system_node_ids:
            cross_classifications = await repo.get_cross_classifications(node_id)
            for cc in cross_classifications:
                if cc["secondary_node_id"] == discipline_id:
                    node = await self.get_node(node_id)
                    if node:
                        result_nodes.append(node)
                    break

        return result_nodes

    async def get_first_aid_page(self, node_id: str) -> int | None:
        """Get the First Aid page number for a node."""
        repo = await self._get_repo()
        resources = await repo.get_resources_for_node(node_id)

        for resource in resources:
            if "first aid" in resource.get("resource_name", "").lower():
                section_id = resource.get("section_id")
                if section_id:
                    conn = await repo._get_connection()
                    cursor = await conn.execute(
                        "SELECT page_start FROM resource_sections WHERE id = ?",
                        (section_id,),
                    )
                    row = await cursor.fetchone()
                    if row:
                        return row[0]

        return None

    async def generate_anking_tag(self, node_id: str) -> str:
        """Generate an AnKing-style tag for a node."""
        node = await self.get_node(node_id)
        if node is None:
            return ""

        path_parts = []
        if node.exam_id == "MCAT":
            path_parts.append("#AK_MCAT")
        elif node.exam_id == "USMLE_STEP1":
            path_parts.append("#AK_Step1_v12")
        else:
            path_parts.append("#AK")

        repo = await self._get_repo()
        path = await repo.get_path(node_id)

        for part in path:
            sanitized = self._sanitize_tag_component(part)
            path_parts.append(sanitized)

        return "::".join(path_parts)

    def _sanitize_tag_component(self, text: str) -> str:
        """Sanitize text for use in Anki tag."""
        text = re.sub(r"[^a-zA-Z0-9_\-\s]", "", text)
        text = re.sub(r"\s+", "_", text.strip())
        return text

    def _exam_type_to_id(self, exam: ExamType) -> str:
        """Convert ExamType enum to database ID."""
        mapping = {
            ExamType.MCAT: "MCAT",
            ExamType.USMLE_STEP1: "USMLE_STEP1",
        }
        return mapping.get(exam, exam.value.upper())
