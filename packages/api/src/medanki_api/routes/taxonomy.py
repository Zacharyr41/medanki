"""Taxonomy API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from medanki.models.enums import ExamType
from medanki.models.taxonomy import TaxonomyNode
from medanki.services.taxonomy_v2 import TaxonomyServiceV2

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])

DB_PATH = Path("data/taxonomy.db")


class ExamsResponse(BaseModel):
    """Response for listing available exams."""

    exams: list[str] = Field(description="List of available exam identifiers")


class NodeResponse(BaseModel):
    """Response for a single taxonomy node."""

    id: str
    exam_id: str
    node_type: str
    code: str | None = None
    title: str
    description: str | None = None
    percentage_min: float | None = None
    percentage_max: float | None = None
    parent_id: str | None = None
    sort_order: int = 0
    keywords: list[str] = Field(default_factory=list)
    depth: int | None = None

    @classmethod
    def from_node(cls, node: TaxonomyNode) -> NodeResponse:
        """Create response from TaxonomyNode."""
        return cls(
            id=node.id,
            exam_id=node.exam_id,
            node_type=node.node_type.value,
            code=node.code,
            title=node.title,
            description=node.description,
            percentage_min=node.percentage_min,
            percentage_max=node.percentage_max,
            parent_id=node.parent_id,
            sort_order=node.sort_order,
            keywords=node.keywords,
            depth=node.depth,
        )


class NodesResponse(BaseModel):
    """Response for a list of taxonomy nodes."""

    nodes: list[NodeResponse] = Field(description="List of taxonomy nodes")


EXAM_MAPPING = {
    "MCAT": ExamType.MCAT,
    "USMLE_STEP1": ExamType.USMLE_STEP1,
    "USMLE_STEP2": ExamType.USMLE_STEP2,
}

AVAILABLE_EXAMS = ["MCAT", "USMLE_STEP1"]


async def get_taxonomy_service() -> TaxonomyServiceV2:
    """Dependency for taxonomy service."""
    return TaxonomyServiceV2(DB_PATH)


@router.get("/exams", response_model=ExamsResponse)
async def get_exams() -> ExamsResponse:
    """Get list of available exams."""
    return ExamsResponse(exams=AVAILABLE_EXAMS)


@router.get("/{exam}/root", response_model=NodesResponse)
async def get_root_nodes(
    exam: str,
    service: Annotated[TaxonomyServiceV2, Depends(get_taxonomy_service)],
) -> NodesResponse:
    """Get root nodes for an exam."""
    if exam not in EXAM_MAPPING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam '{exam}' not found",
        )

    exam_type = EXAM_MAPPING[exam]
    async with service:
        nodes = await service.get_root_nodes(exam_type)

    return NodesResponse(nodes=[NodeResponse.from_node(n) for n in nodes])


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    service: Annotated[TaxonomyServiceV2, Depends(get_taxonomy_service)],
) -> NodeResponse:
    """Get a taxonomy node by ID."""
    async with service:
        node = await service.get_node(node_id)

    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found",
        )

    return NodeResponse.from_node(node)


@router.get("/nodes/{node_id}/children", response_model=NodesResponse)
async def get_children(
    node_id: str,
    service: Annotated[TaxonomyServiceV2, Depends(get_taxonomy_service)],
) -> NodesResponse:
    """Get children of a taxonomy node."""
    async with service:
        children = await service.get_children(node_id)

    return NodesResponse(nodes=[NodeResponse.from_node(n) for n in children])


@router.get("/search", response_model=NodesResponse)
async def search_nodes(
    q: Annotated[str, Query(min_length=1, description="Search query")],
    exam: Annotated[str | None, Query(description="Filter by exam")] = None,
    service: TaxonomyServiceV2 = Depends(get_taxonomy_service),
) -> NodesResponse:
    """Search taxonomy nodes by keyword."""
    exam_type = None
    if exam is not None:
        if exam not in EXAM_MAPPING:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exam '{exam}' not found",
            )
        exam_type = EXAM_MAPPING[exam]

    async with service:
        nodes = await service.search_by_keyword(q, exam_type)

    return NodesResponse(nodes=[NodeResponse.from_node(n) for n in nodes])
