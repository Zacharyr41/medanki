"""Tests for taxonomy domain models."""

from __future__ import annotations

import pytest

from medanki.models.taxonomy import (
    CrossClassification,
    NodeType,
    ResourceMapping,
    TaxonomyNode,
)


class TestNodeType:
    """Tests for NodeType enumeration."""

    def test_foundational_concept_value(self):
        assert NodeType.FOUNDATIONAL_CONCEPT.value == "foundational_concept"

    def test_content_category_value(self):
        assert NodeType.CONTENT_CATEGORY.value == "content_category"

    def test_topic_value(self):
        assert NodeType.TOPIC.value == "topic"

    def test_subtopic_value(self):
        assert NodeType.SUBTOPIC.value == "subtopic"

    def test_organ_system_value(self):
        assert NodeType.ORGAN_SYSTEM.value == "organ_system"

    def test_discipline_value(self):
        assert NodeType.DISCIPLINE.value == "discipline"

    def test_section_value(self):
        assert NodeType.SECTION.value == "section"

    def test_all_node_types_exist(self):
        expected = {
            "FOUNDATIONAL_CONCEPT",
            "CONTENT_CATEGORY",
            "TOPIC",
            "SUBTOPIC",
            "ORGAN_SYSTEM",
            "DISCIPLINE",
            "SECTION",
        }
        actual = {n.name for n in NodeType}
        assert actual == expected

    def test_node_type_is_str_enum(self):
        assert isinstance(NodeType.TOPIC.value, str)
        assert NodeType.TOPIC == "topic"


class TestTaxonomyNode:
    """Tests for TaxonomyNode model."""

    def test_node_creation_with_required_fields(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Biomolecules",
        )
        assert node.id == "FC1"
        assert node.exam_id == "MCAT"
        assert node.node_type == NodeType.FOUNDATIONAL_CONCEPT
        assert node.title == "Biomolecules"

    def test_node_creation_with_all_fields(self):
        node = TaxonomyNode(
            id="1A",
            exam_id="MCAT",
            node_type=NodeType.CONTENT_CATEGORY,
            code="1A",
            title="Proteins and Amino Acids",
            description="Structure and function of proteins",
            percentage_min=10.0,
            percentage_max=15.0,
            parent_id="FC1",
            sort_order=1,
            metadata={"importance": "high"},
            keywords=["protein", "amino acid"],
            depth=1,
        )
        assert node.id == "1A"
        assert node.code == "1A"
        assert node.description == "Structure and function of proteins"
        assert node.percentage_min == 10.0
        assert node.percentage_max == 15.0
        assert node.parent_id == "FC1"
        assert node.sort_order == 1
        assert node.metadata == {"importance": "high"}
        assert node.keywords == ["protein", "amino acid"]
        assert node.depth == 1

    def test_node_defaults(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
        )
        assert node.code is None
        assert node.description is None
        assert node.percentage_min is None
        assert node.percentage_max is None
        assert node.parent_id is None
        assert node.sort_order == 0
        assert node.metadata is None
        assert node.keywords == []
        assert node.depth is None

    def test_is_root_property_true(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Root Node",
            parent_id=None,
        )
        assert node.is_root is True

    def test_is_root_property_false(self):
        node = TaxonomyNode(
            id="1A",
            exam_id="MCAT",
            node_type=NodeType.CONTENT_CATEGORY,
            title="Child Node",
            parent_id="FC1",
        )
        assert node.is_root is False

    def test_is_leaf_property(self):
        node = TaxonomyNode(
            id="1A_1",
            exam_id="MCAT",
            node_type=NodeType.TOPIC,
            title="Leaf Node",
            parent_id="1A",
        )
        assert node.is_leaf is False

    def test_node_type_validation(self):
        node = TaxonomyNode(
            id="SYS1",
            exam_id="USMLE_STEP1",
            node_type=NodeType.ORGAN_SYSTEM,
            title="Cardiovascular System",
        )
        assert node.node_type == NodeType.ORGAN_SYSTEM

    def test_percentage_min_validation_lower_bound(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="FC1",
                exam_id="MCAT",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="Test",
                percentage_min=-1.0,
            )

    def test_percentage_min_validation_upper_bound(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="FC1",
                exam_id="MCAT",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="Test",
                percentage_min=101.0,
            )

    def test_percentage_max_validation_lower_bound(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="FC1",
                exam_id="MCAT",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="Test",
                percentage_max=-1.0,
            )

    def test_percentage_max_validation_upper_bound(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="FC1",
                exam_id="MCAT",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="Test",
                percentage_max=101.0,
            )

    def test_percentage_bounds_valid(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
            percentage_min=0.0,
            percentage_max=100.0,
        )
        assert node.percentage_min == 0.0
        assert node.percentage_max == 100.0

    def test_id_min_length_validation(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="",
                exam_id="MCAT",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="Test",
            )

    def test_exam_id_min_length_validation(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="FC1",
                exam_id="",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="Test",
            )

    def test_title_min_length_validation(self):
        with pytest.raises(ValueError):
            TaxonomyNode(
                id="FC1",
                exam_id="MCAT",
                node_type=NodeType.FOUNDATIONAL_CONCEPT,
                title="",
            )

    def test_node_serialization(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Biomolecules",
            keywords=["biology", "chemistry"],
        )
        data = node.model_dump()
        assert data["id"] == "FC1"
        assert data["exam_id"] == "MCAT"
        assert data["node_type"] == "foundational_concept"
        assert data["title"] == "Biomolecules"
        assert data["keywords"] == ["biology", "chemistry"]

    def test_node_from_dict(self):
        data = {
            "id": "FC1",
            "exam_id": "MCAT",
            "node_type": "foundational_concept",
            "title": "Biomolecules",
        }
        node = TaxonomyNode.model_validate(data)
        assert node.id == "FC1"
        assert node.node_type == NodeType.FOUNDATIONAL_CONCEPT


class TestResourceMapping:
    """Tests for ResourceMapping model."""

    def test_mapping_creation_with_required_fields(self):
        mapping = ResourceMapping(
            section_id="fa_cardio",
            section_title="Cardiovascular",
            resource_name="First Aid",
        )
        assert mapping.section_id == "fa_cardio"
        assert mapping.section_title == "Cardiovascular"
        assert mapping.resource_name == "First Aid"

    def test_mapping_defaults(self):
        mapping = ResourceMapping(
            section_id="fa_cardio",
            section_title="Cardiovascular",
            resource_name="First Aid",
        )
        assert mapping.relevance_score == 1.0
        assert mapping.is_primary is False
        assert mapping.page_start is None
        assert mapping.page_end is None

    def test_mapping_with_all_fields(self):
        mapping = ResourceMapping(
            section_id="fa_cardio_hf",
            section_title="Heart Failure",
            resource_name="First Aid 2024",
            relevance_score=0.95,
            is_primary=True,
            page_start=305,
            page_end=310,
        )
        assert mapping.relevance_score == 0.95
        assert mapping.is_primary is True
        assert mapping.page_start == 305
        assert mapping.page_end == 310

    def test_relevance_score_lower_bound(self):
        with pytest.raises(ValueError):
            ResourceMapping(
                section_id="fa_cardio",
                section_title="Test",
                resource_name="First Aid",
                relevance_score=-0.1,
            )

    def test_relevance_score_upper_bound(self):
        with pytest.raises(ValueError):
            ResourceMapping(
                section_id="fa_cardio",
                section_title="Test",
                resource_name="First Aid",
                relevance_score=1.1,
            )

    def test_relevance_score_valid_bounds(self):
        mapping_min = ResourceMapping(
            section_id="test1",
            section_title="Test",
            resource_name="First Aid",
            relevance_score=0.0,
        )
        mapping_max = ResourceMapping(
            section_id="test2",
            section_title="Test",
            resource_name="First Aid",
            relevance_score=1.0,
        )
        assert mapping_min.relevance_score == 0.0
        assert mapping_max.relevance_score == 1.0

    def test_mapping_serialization(self):
        mapping = ResourceMapping(
            section_id="fa_cardio",
            section_title="Cardiovascular",
            resource_name="First Aid",
            is_primary=True,
        )
        data = mapping.model_dump()
        assert data["section_id"] == "fa_cardio"
        assert data["is_primary"] is True


class TestCrossClassification:
    """Tests for CrossClassification model."""

    def test_cross_classification_creation(self):
        cc = CrossClassification(
            primary_node_id="CARDIO",
            secondary_node_id="PATHOLOGY",
            relationship_type="system_discipline",
        )
        assert cc.primary_node_id == "CARDIO"
        assert cc.secondary_node_id == "PATHOLOGY"
        assert cc.relationship_type == "system_discipline"

    def test_cross_classification_default_weight(self):
        cc = CrossClassification(
            primary_node_id="CARDIO",
            secondary_node_id="PATHOLOGY",
            relationship_type="system_discipline",
        )
        assert cc.weight == 1.0

    def test_cross_classification_custom_weight(self):
        cc = CrossClassification(
            primary_node_id="CARDIO",
            secondary_node_id="PATHOLOGY",
            relationship_type="system_discipline",
            weight=0.8,
        )
        assert cc.weight == 0.8

    def test_weight_lower_bound(self):
        with pytest.raises(ValueError):
            CrossClassification(
                primary_node_id="CARDIO",
                secondary_node_id="PATHOLOGY",
                relationship_type="system_discipline",
                weight=-0.1,
            )

    def test_weight_upper_bound(self):
        with pytest.raises(ValueError):
            CrossClassification(
                primary_node_id="CARDIO",
                secondary_node_id="PATHOLOGY",
                relationship_type="system_discipline",
                weight=1.1,
            )

    def test_weight_valid_bounds(self):
        cc_min = CrossClassification(
            primary_node_id="CARDIO",
            secondary_node_id="PATHOLOGY",
            relationship_type="test",
            weight=0.0,
        )
        cc_max = CrossClassification(
            primary_node_id="CARDIO",
            secondary_node_id="PATHOLOGY",
            relationship_type="test",
            weight=1.0,
        )
        assert cc_min.weight == 0.0
        assert cc_max.weight == 1.0

    def test_cross_classification_serialization(self):
        cc = CrossClassification(
            primary_node_id="CARDIO",
            secondary_node_id="PATHOLOGY",
            relationship_type="system_discipline",
            weight=0.9,
        )
        data = cc.model_dump()
        assert data["primary_node_id"] == "CARDIO"
        assert data["secondary_node_id"] == "PATHOLOGY"
        assert data["weight"] == 0.9


class TestTaxonomyNodeWithDifferentExams:
    """Tests for TaxonomyNode with MCAT and USMLE exams."""

    def test_mcat_foundational_concept(self):
        node = TaxonomyNode(
            id="MCAT_FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            code="FC1",
            title="Biomolecules",
            percentage_min=10,
            percentage_max=15,
        )
        assert node.exam_id == "MCAT"
        assert node.node_type == NodeType.FOUNDATIONAL_CONCEPT

    def test_mcat_content_category(self):
        node = TaxonomyNode(
            id="MCAT_1A",
            exam_id="MCAT",
            node_type=NodeType.CONTENT_CATEGORY,
            code="1A",
            title="Proteins and Amino Acids",
            parent_id="MCAT_FC1",
        )
        assert node.node_type == NodeType.CONTENT_CATEGORY
        assert node.parent_id == "MCAT_FC1"

    def test_usmle_organ_system(self):
        node = TaxonomyNode(
            id="USMLE_CARDIO",
            exam_id="USMLE_STEP1",
            node_type=NodeType.ORGAN_SYSTEM,
            code="CARDIO",
            title="Cardiovascular System",
        )
        assert node.exam_id == "USMLE_STEP1"
        assert node.node_type == NodeType.ORGAN_SYSTEM

    def test_usmle_discipline(self):
        node = TaxonomyNode(
            id="USMLE_PATH",
            exam_id="USMLE_STEP1",
            node_type=NodeType.DISCIPLINE,
            code="PATH",
            title="Pathology",
        )
        assert node.node_type == NodeType.DISCIPLINE


class TestTaxonomyNodeKeywords:
    """Tests for TaxonomyNode keyword handling."""

    def test_empty_keywords(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
        )
        assert node.keywords == []

    def test_single_keyword(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
            keywords=["protein"],
        )
        assert node.keywords == ["protein"]

    def test_multiple_keywords(self):
        keywords = ["protein", "enzyme", "amino acid", "peptide"]
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
            keywords=keywords,
        )
        assert node.keywords == keywords
        assert len(node.keywords) == 4

    def test_keywords_preserved_order(self):
        keywords = ["first", "second", "third"]
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
            keywords=keywords,
        )
        assert node.keywords[0] == "first"
        assert node.keywords[2] == "third"


class TestTaxonomyNodeMetadata:
    """Tests for TaxonomyNode metadata handling."""

    def test_none_metadata(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
        )
        assert node.metadata is None

    def test_empty_dict_metadata(self):
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
            metadata={},
        )
        assert node.metadata == {}

    def test_complex_metadata(self):
        metadata = {
            "source": "AAMC Blueprint",
            "last_updated": "2024-01-15",
            "tags": ["high-yield", "common"],
            "nested": {"level": 1, "importance": "high"},
        }
        node = TaxonomyNode(
            id="FC1",
            exam_id="MCAT",
            node_type=NodeType.FOUNDATIONAL_CONCEPT,
            title="Test",
            metadata=metadata,
        )
        assert node.metadata["source"] == "AAMC Blueprint"
        assert node.metadata["tags"] == ["high-yield", "common"]
        assert node.metadata["nested"]["importance"] == "high"
