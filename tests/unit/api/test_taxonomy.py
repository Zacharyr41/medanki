"""Tests for taxonomy API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from medanki.models.taxonomy import NodeType, TaxonomyNode


@pytest.fixture
def mock_taxonomy_service():
    """Create a mock taxonomy service."""
    service = AsyncMock()
    return service


@pytest.fixture
def client(mock_taxonomy_service):
    """Create a test client with mocked taxonomy service."""
    from medanki_api.main import app
    from medanki_api.routes.taxonomy import get_taxonomy_service

    app.dependency_overrides[get_taxonomy_service] = lambda: mock_taxonomy_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetExams:
    """Tests for GET /taxonomy/exams endpoint."""

    def test_returns_list_of_exams(self, client):
        """Should return list of available exams."""
        response = client.get("/taxonomy/exams")

        assert response.status_code == 200
        data = response.json()
        assert "exams" in data
        assert "MCAT" in data["exams"]
        assert "USMLE_STEP1" in data["exams"]

    def test_exams_response_format(self, client):
        """Should return exams with proper metadata."""
        response = client.get("/taxonomy/exams")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["exams"], list)


class TestGetRootNodes:
    """Tests for GET /taxonomy/{exam}/root endpoint."""

    def test_returns_root_nodes_for_mcat(self, client, mock_taxonomy_service):
        """Should return root nodes for MCAT."""
        mock_nodes = [
            TaxonomyNode(
                id="mcat-1",
                exam_id="MCAT",
                node_type=NodeType.SECTION,
                title="Biological and Biochemical Foundations",
                sort_order=1,
            ),
            TaxonomyNode(
                id="mcat-2",
                exam_id="MCAT",
                node_type=NodeType.SECTION,
                title="Chemical and Physical Foundations",
                sort_order=2,
            ),
        ]
        mock_taxonomy_service.get_root_nodes.return_value = mock_nodes

        response = client.get("/taxonomy/MCAT/root")

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert len(data["nodes"]) == 2
        assert data["nodes"][0]["title"] == "Biological and Biochemical Foundations"

    def test_returns_root_nodes_for_usmle(self, client, mock_taxonomy_service):
        """Should return root nodes for USMLE."""
        mock_nodes = [
            TaxonomyNode(
                id="usmle-1",
                exam_id="USMLE_STEP1",
                node_type=NodeType.ORGAN_SYSTEM,
                title="General Principles",
                sort_order=1,
            ),
        ]
        mock_taxonomy_service.get_root_nodes.return_value = mock_nodes

        response = client.get("/taxonomy/USMLE_STEP1/root")

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1

    def test_invalid_exam_returns_404(self, client, mock_taxonomy_service):
        """Should return 404 for invalid exam."""
        response = client.get("/taxonomy/INVALID/root")

        assert response.status_code == 404


class TestGetNode:
    """Tests for GET /taxonomy/nodes/{node_id} endpoint."""

    def test_returns_node_by_id(self, client, mock_taxonomy_service):
        """Should return a node by its ID."""
        mock_node = TaxonomyNode(
            id="mcat-bio-1",
            exam_id="MCAT",
            node_type=NodeType.TOPIC,
            title="Amino Acids",
            keywords=["amino acid", "protein", "peptide"],
        )
        mock_taxonomy_service.get_node.return_value = mock_node

        response = client.get("/taxonomy/nodes/mcat-bio-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "mcat-bio-1"
        assert data["title"] == "Amino Acids"
        assert "amino acid" in data["keywords"]

    def test_nonexistent_node_returns_404(self, client, mock_taxonomy_service):
        """Should return 404 for nonexistent node."""
        mock_taxonomy_service.get_node.return_value = None

        response = client.get("/taxonomy/nodes/nonexistent")

        assert response.status_code == 404


class TestGetChildren:
    """Tests for GET /taxonomy/nodes/{node_id}/children endpoint."""

    def test_returns_children_of_node(self, client, mock_taxonomy_service):
        """Should return children of a node."""
        mock_children = [
            TaxonomyNode(
                id="child-1",
                exam_id="MCAT",
                node_type=NodeType.TOPIC,
                title="Protein Structure",
                parent_id="mcat-bio-1",
            ),
            TaxonomyNode(
                id="child-2",
                exam_id="MCAT",
                node_type=NodeType.TOPIC,
                title="Enzyme Kinetics",
                parent_id="mcat-bio-1",
            ),
        ]
        mock_taxonomy_service.get_children.return_value = mock_children

        response = client.get("/taxonomy/nodes/mcat-bio-1/children")

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2


class TestSearchNodes:
    """Tests for GET /taxonomy/search endpoint."""

    def test_search_by_keyword(self, client, mock_taxonomy_service):
        """Should search nodes by keyword."""
        mock_results = [
            TaxonomyNode(
                id="mcat-bio-1",
                exam_id="MCAT",
                node_type=NodeType.TOPIC,
                title="Amino Acids",
                keywords=["amino acid"],
            ),
        ]
        mock_taxonomy_service.search_by_keyword.return_value = mock_results

        response = client.get("/taxonomy/search?q=amino")

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        mock_taxonomy_service.search_by_keyword.assert_called()

    def test_search_with_exam_filter(self, client, mock_taxonomy_service):
        """Should filter search by exam."""
        mock_taxonomy_service.search_by_keyword.return_value = []

        response = client.get("/taxonomy/search?q=cardio&exam=MCAT")

        assert response.status_code == 200
        mock_taxonomy_service.search_by_keyword.assert_called_once()
