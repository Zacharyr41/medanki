"""Tests for Anki tag building."""


from packages.core.src.medanki.export.tags import TagBuilder


class TestTagBuilder:
    def test_builds_mcat_tags(self):
        """'FC1 > 1A' -> '#MCAT::FC1::1A'"""
        builder = TagBuilder()
        result = builder.build_mcat_tag("FC1 > 1A")
        assert result == "#MCAT::FC1::1A"

    def test_builds_usmle_tags(self):
        """AnKing format '#AK_Step1_v12::...'"""
        builder = TagBuilder()
        result = builder.build_usmle_tag("Step1", "Cardiology", "Heart Failure")
        assert result == "#AK_Step1_v12::Cardiology::Heart_Failure"

    def test_includes_source_tag(self):
        """'#Source::MedAnki::lecture_name'"""
        builder = TagBuilder()
        result = builder.build_source_tag("Biochemistry Lecture 5")
        assert result == "#Source::MedAnki::Biochemistry_Lecture_5"

    def test_hierarchical_format(self):
        """Proper :: separators"""
        builder = TagBuilder()
        result = builder.build_hierarchical_tag(["Category", "Subcategory", "Topic"])
        assert result == "#Category::Subcategory::Topic"

    def test_sanitizes_special_chars(self):
        """Removes spaces, quotes"""
        builder = TagBuilder()
        result = builder.sanitize("Heart's \"Anatomy\" Test")
        assert result == "Hearts_Anatomy_Test"

    def test_sanitizes_multiple_spaces(self):
        builder = TagBuilder()
        result = builder.sanitize("Multiple   spaces   here")
        assert result == "Multiple_spaces_here"

    def test_empty_path_returns_empty(self):
        builder = TagBuilder()
        result = builder.build_hierarchical_tag([])
        assert result == ""

    def test_mcat_tag_with_special_chars(self):
        builder = TagBuilder()
        result = builder.build_mcat_tag("FC2 > 2B: Proteins")
        assert result == "#MCAT::FC2::2B_Proteins"
