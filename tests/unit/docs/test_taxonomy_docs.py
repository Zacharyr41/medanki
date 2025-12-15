"""Tests for taxonomy documentation completeness."""

from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).parents[3] / "docs"
ROOT_DIR = Path(__file__).parents[3]


class TestReadmeTaxonomySection:
    """Tests for taxonomy section in README.md."""

    @pytest.fixture
    def readme_content(self) -> str:
        readme_path = ROOT_DIR / "README.md"
        return readme_path.read_text()

    def test_has_taxonomy_section(self, readme_content: str) -> None:
        assert "## Taxonomy" in readme_content or "### Taxonomy" in readme_content

    def test_mentions_mcat(self, readme_content: str) -> None:
        assert "MCAT" in readme_content

    def test_mentions_usmle(self, readme_content: str) -> None:
        assert "USMLE" in readme_content

    def test_links_to_taxonomy_docs(self, readme_content: str) -> None:
        assert "docs/taxonomy.md" in readme_content


class TestArchitectureDoc:
    """Tests for architecture documentation."""

    @pytest.fixture
    def architecture_content(self) -> str:
        arch_path = DOCS_DIR / "architecture.md"
        return arch_path.read_text()

    def test_has_taxonomy_section(self, architecture_content: str) -> None:
        assert "Taxonomy" in architecture_content

    def test_mentions_sqlite_backend(self, architecture_content: str) -> None:
        assert "SQLite" in architecture_content

    def test_mentions_closure_table(self, architecture_content: str) -> None:
        assert "closure" in architecture_content.lower()

    def test_mentions_taxonomy_service(self, architecture_content: str) -> None:
        assert "TaxonomyService" in architecture_content

    def test_mentions_mesh_integration(self, architecture_content: str) -> None:
        assert "MeSH" in architecture_content


class TestTaxonomyDoc:
    """Tests for taxonomy documentation."""

    @pytest.fixture
    def taxonomy_content(self) -> str:
        tax_path = DOCS_DIR / "taxonomy.md"
        return tax_path.read_text()

    def test_has_database_schema_section(self, taxonomy_content: str) -> None:
        assert "Database Schema" in taxonomy_content or "Schema" in taxonomy_content

    def test_documents_node_types(self, taxonomy_content: str) -> None:
        assert "NodeType" in taxonomy_content or "node_type" in taxonomy_content

    def test_documents_closure_table(self, taxonomy_content: str) -> None:
        assert "closure" in taxonomy_content.lower()

    def test_documents_keywords(self, taxonomy_content: str) -> None:
        assert "keyword" in taxonomy_content.lower()

    def test_documents_cross_classification(self, taxonomy_content: str) -> None:
        assert "cross" in taxonomy_content.lower()

    def test_documents_resource_mappings(self, taxonomy_content: str) -> None:
        assert "resource" in taxonomy_content.lower()

    def test_documents_anking_tags(self, taxonomy_content: str) -> None:
        assert "AnKing" in taxonomy_content or "anking" in taxonomy_content.lower()


class TestDataSourcesDoc:
    """Tests for data sources documentation."""

    @pytest.fixture
    def data_sources_content(self) -> str:
        ds_path = DOCS_DIR / "data-sources.md"
        return ds_path.read_text()

    def test_file_exists(self) -> None:
        ds_path = DOCS_DIR / "data-sources.md"
        assert ds_path.exists(), "docs/data-sources.md should exist"

    def test_documents_mcat_json(self, data_sources_content: str) -> None:
        assert "mcat.json" in data_sources_content

    def test_documents_usmle_json(self, data_sources_content: str) -> None:
        assert "usmle_step1.json" in data_sources_content

    def test_documents_mesh_api(self, data_sources_content: str) -> None:
        assert "MeSH" in data_sources_content

    def test_documents_huggingface(self, data_sources_content: str) -> None:
        assert "Hugging Face" in data_sources_content or "HuggingFace" in data_sources_content

    def test_documents_anking(self, data_sources_content: str) -> None:
        assert "AnKing" in data_sources_content

    def test_documents_medmcqa(self, data_sources_content: str) -> None:
        assert "MedMCQA" in data_sources_content

    def test_has_ingestion_section(self, data_sources_content: str) -> None:
        assert "Ingestion" in data_sources_content or "ingestion" in data_sources_content
