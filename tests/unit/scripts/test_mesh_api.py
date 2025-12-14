#!/usr/bin/env python3
"""Tests for MeSH API client."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.ingest.mesh_api import MeshAPIClient, MeshConcept


class TestMeshConcept:
    def test_mesh_concept_creation(self):
        concept = MeshConcept(
            mesh_id="D006333",
            name="Heart Failure",
            tree_numbers=["C14.280.434"],
            synonyms=["Cardiac Failure", "Heart Decompensation"],
        )
        assert concept.mesh_id == "D006333"
        assert concept.name == "Heart Failure"
        assert len(concept.tree_numbers) == 1
        assert len(concept.synonyms) == 2


class TestMeshAPIClientInit:
    def test_default_cache_dir(self):
        client = MeshAPIClient()
        assert client.cache_dir == Path.home() / ".cache" / "medanki" / "mesh"

    def test_custom_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "custom_cache"
            client = MeshAPIClient(cache_dir=cache_path)
            assert client.cache_dir == cache_path
            assert cache_path.exists()


class TestMeshAPIClientSearch:
    @patch("scripts.ingest.mesh_api.requests.get")
    def test_search_returns_mesh_concepts(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "d": {"value": "http://id.nlm.nih.gov/mesh/D006333"},
                        "label": {"value": "Heart Failure"},
                        "treeNumber": {"value": "C14.280.434"},
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            results = client.search("heart failure")

        assert len(results) == 1
        assert results[0].mesh_id == "D006333"
        assert results[0].name == "Heart Failure"

    @patch("scripts.ingest.mesh_api.requests.get")
    def test_search_empty_results(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            results = client.search("nonexistent12345")

        assert len(results) == 0

    @patch("scripts.ingest.mesh_api.requests.get")
    def test_search_uses_sparql_endpoint(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            client.search("test")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "id.nlm.nih.gov/mesh/sparql" in call_args[0][0]


class TestMeshAPIClientGetSynonyms:
    @patch("scripts.ingest.mesh_api.requests.get")
    def test_get_synonyms_returns_list(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {"altLabel": {"value": "Cardiac Failure"}},
                    {"altLabel": {"value": "Heart Decompensation"}},
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            synonyms = client.get_synonyms("Heart Failure")

        assert "Cardiac Failure" in synonyms
        assert "Heart Decompensation" in synonyms

    @patch("scripts.ingest.mesh_api.requests.get")
    def test_get_synonyms_no_results(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            synonyms = client.get_synonyms("Unknown Term")

        assert synonyms == []


class TestMeshAPIClientCaching:
    @patch("scripts.ingest.mesh_api.requests.get")
    def test_search_uses_cache(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "d": {"value": "http://id.nlm.nih.gov/mesh/D006333"},
                        "label": {"value": "Heart Failure"},
                        "treeNumber": {"value": "C14.280.434"},
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            client.search("heart failure")
            client.search("heart failure")

        assert mock_get.call_count == 1

    @patch("scripts.ingest.mesh_api.requests.get")
    def test_get_synonyms_uses_cache(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": {
                "bindings": [{"altLabel": {"value": "Cardiac Failure"}}]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            client.get_synonyms("Heart Failure")
            client.get_synonyms("Heart Failure")

        assert mock_get.call_count == 1


class TestMeshAPIClientRateLimiting:
    @patch("scripts.ingest.mesh_api.time.sleep")
    @patch("scripts.ingest.mesh_api.requests.get")
    def test_rate_limiting_applied(self, mock_get, mock_sleep):
        mock_response = Mock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            client.search("term1")
            client.search("term2")

        assert mock_sleep.call_count >= 1
        mock_sleep.assert_called_with(0.1)


class TestMeshAPIClientGetConcept:
    @patch("scripts.ingest.mesh_api.requests.get")
    def test_get_concept_rest_api(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "@id": "http://id.nlm.nih.gov/mesh/D006333",
            "label": {"@value": "Heart Failure"},
            "treeNumber": [{"@value": "C14.280.434"}],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            concept = client.get_concept("D006333")

        assert concept is not None
        assert concept.mesh_id == "D006333"
        mock_get.assert_called_once()
        assert "D006333.json" in mock_get.call_args[0][0]


class TestBuildVocab:
    @patch("scripts.ingest.mesh_api.MeshAPIClient.get_category_descriptors")
    def test_build_vocab_creates_json(self, mock_get_cat):
        mock_get_cat.return_value = [
            MeshConcept(
                mesh_id="D006333",
                name="Heart Failure",
                tree_numbers=["C14.280.434"],
                synonyms=["Cardiac Failure"],
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "mesh_vocab.json"
            client = MeshAPIClient(cache_dir=Path(tmpdir))
            client.build_vocab(categories=["C"], output=output_path)

            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            assert "D006333" in data
            assert data["D006333"]["name"] == "Heart Failure"
