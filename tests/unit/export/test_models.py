"""Tests for Anki model definitions."""


from packages.core.src.medanki.export.models import (
    CLOZE_MODEL_ID,
    VIGNETTE_MODEL_ID,
    get_cloze_model,
    get_vignette_model,
)


class TestClozeModel:
    def test_cloze_model_id_stable(self):
        """ID never changes - critical for Anki updates."""
        assert CLOZE_MODEL_ID == 1607392319001

    def test_cloze_model_has_fields(self):
        """Text, Extra, Source fields."""
        model = get_cloze_model()
        field_names = [f["name"] for f in model.fields]
        assert "Text" in field_names
        assert "Extra" in field_names
        assert "Source" in field_names

    def test_cloze_model_is_cloze_type(self):
        model = get_cloze_model()
        assert model.model_type == 1

    def test_model_css_applied(self):
        """Styling included."""
        model = get_cloze_model()
        assert model.css is not None
        assert len(model.css) > 0


class TestVignetteModel:
    def test_vignette_model_id_stable(self):
        """ID never changes - critical for Anki updates."""
        assert VIGNETTE_MODEL_ID == 1607392319003

    def test_vignette_model_has_fields(self):
        """All required fields."""
        model = get_vignette_model()
        field_names = [f["name"] for f in model.fields]
        assert "Front" in field_names
        assert "Answer" in field_names
        assert "Explanation" in field_names
        assert "DistinguishingFeature" in field_names
        assert "Source" in field_names

    def test_vignette_model_is_basic_type(self):
        model = get_vignette_model()
        assert model.model_type == 0

    def test_vignette_model_css_applied(self):
        model = get_vignette_model()
        assert model.css is not None
        assert len(model.css) > 0
