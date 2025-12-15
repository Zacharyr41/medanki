"""Taxonomy domain models for MedAnki."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of taxonomy nodes in the hierarchy."""

    FOUNDATIONAL_CONCEPT = "foundational_concept"
    CONTENT_CATEGORY = "content_category"
    TOPIC = "topic"
    SUBTOPIC = "subtopic"
    ORGAN_SYSTEM = "organ_system"
    DISCIPLINE = "discipline"
    SECTION = "section"


class TaxonomyNode(BaseModel):
    """A node in the taxonomy hierarchy.

    Represents a single topic/concept in the MCAT or USMLE taxonomy tree.
    """

    id: str = Field(..., min_length=1, description="Unique node identifier")
    exam_id: str = Field(..., min_length=1, description="Parent exam ID (MCAT, USMLE_STEP1)")
    node_type: NodeType = Field(..., description="Type of node in hierarchy")
    code: str | None = Field(default=None, description="Official code (e.g., 1A, FC1)")
    title: str = Field(..., min_length=1, description="Display title")
    description: str | None = Field(default=None, description="Detailed description")
    percentage_min: float | None = Field(
        default=None, ge=0, le=100, description="Min exam weight %"
    )
    percentage_max: float | None = Field(
        default=None, ge=0, le=100, description="Max exam weight %"
    )
    parent_id: str | None = Field(default=None, description="Parent node ID")
    sort_order: int = Field(default=0, description="Display order among siblings")
    metadata: dict | None = Field(default=None, description="Additional metadata")
    keywords: list[str] = Field(default_factory=list, description="Associated keywords")
    depth: int | None = Field(default=None, description="Depth in hierarchy (from closure table)")

    @property
    def is_root(self) -> bool:
        """Check if this is a root node (no parent)."""
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (determined externally)."""
        return False


class ResourceMapping(BaseModel):
    """Mapping between a taxonomy node and an external resource section."""

    section_id: str = Field(..., description="Resource section ID")
    section_title: str = Field(..., description="Resource section title")
    resource_name: str = Field(..., description="Resource name (e.g., First Aid)")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    is_primary: bool = Field(default=False)
    page_start: int | None = Field(default=None, description="Start page number")
    page_end: int | None = Field(default=None, description="End page number")


class CrossClassification(BaseModel):
    """Cross-classification relationship between two taxonomy nodes.

    Used for USMLE system × discipline mappings.
    """

    primary_node_id: str = Field(..., description="Primary node (e.g., organ system)")
    secondary_node_id: str = Field(..., description="Secondary node (e.g., discipline)")
    relationship_type: str = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
