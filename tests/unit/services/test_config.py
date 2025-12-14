"""Tests for the config service."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass


class TestSettings:
    """Tests for Settings class."""

    def test_settings_loads_from_env(self) -> None:
        """Settings reads ANTHROPIC_API_KEY from environment."""
        from medanki.services.config import Settings

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key-12345"}):
            settings = Settings()
            assert settings.anthropic_api_key == "test-api-key-12345"

    def test_settings_has_defaults(self) -> None:
        """Settings has default values for optional configuration."""
        from medanki.services.config import Settings

        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=True,
        ):
            settings = Settings()
            assert settings.weaviate_url == "http://localhost:8080"
            assert settings.debug is False
            assert settings.enable_vignettes is True
            assert settings.max_cards_per_chunk == 5
            assert settings.chunk_size == 512
            assert settings.chunk_overlap == 75
            assert settings.embedding_dim == 768
            assert settings.base_threshold == 0.65
            assert settings.relative_threshold == 0.80
            assert settings.hybrid_alpha == 0.5

    def test_settings_validates_required(self) -> None:
        """Missing ANTHROPIC_API_KEY raises ValidationError."""
        from pydantic import ValidationError

        from medanki.services.config import Settings

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValidationError):
                Settings()

    def test_get_settings_is_singleton(self) -> None:
        """Multiple calls to get_settings return the same instance."""
        from medanki.services.config import get_settings

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2
