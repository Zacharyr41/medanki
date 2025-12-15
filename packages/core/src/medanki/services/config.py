"""Configuration service using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required:
        anthropic_api_key: API key for Anthropic Claude API.

    Optional:
        weaviate_url: URL for Weaviate vector database.
        debug: Enable debug logging.
        enable_vignettes: Generate clinical vignette cards.
        max_cards_per_chunk: Maximum cards to generate per chunk.
        chunk_size: Size of text chunks in tokens.
        chunk_overlap: Overlap between chunks in tokens.
        embedding_dim: Dimension of embedding vectors.
        base_threshold: Base classification threshold.
        relative_threshold: Relative classification threshold.
        hybrid_alpha: Balance between BM25 and semantic search.
    """

    model_config = SettingsConfigDict(
        env_prefix="MEDANKI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str

    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str | None = None
    debug: bool = False
    enable_vignettes: bool = True
    max_cards_per_chunk: int = 5

    chunk_size: int = 512
    chunk_overlap: int = 75
    embedding_dim: int = 768

    base_threshold: float = 0.65
    relative_threshold: float = 0.80
    hybrid_alpha: float = 0.5

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
        cls,
        settings_cls: type[BaseSettings],
        init_settings: object,
        env_settings: object,
        dotenv_settings: object,
        file_secret_settings: object,
    ) -> tuple[object, ...]:
        """Customize settings sources to handle ANTHROPIC_API_KEY without prefix."""
        from pydantic_settings import EnvSettingsSource

        class AnthropicEnvSource(EnvSettingsSource):
            def get_field_value(  # type: ignore[override]
                self,
                field: object,
                field_name: str,
            ) -> tuple[object, str, bool]:
                import os

                if field_name == "anthropic_api_key":
                    val = os.environ.get("ANTHROPIC_API_KEY")
                    if val is not None:
                        return val, "ANTHROPIC_API_KEY", False
                if field_name == "weaviate_url":
                    val = os.environ.get("WEAVIATE_URL")
                    if val is not None:
                        return val, "WEAVIATE_URL", False
                if field_name == "weaviate_api_key":
                    val = os.environ.get("WEAVIATE_API_KEY")
                    if val is not None:
                        return val, "WEAVIATE_API_KEY", False
                return super().get_field_value(field, field_name)  # type: ignore[arg-type]

        return (
            init_settings,
            AnthropicEnvSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings singleton.

    Returns:
        Settings: The singleton settings instance.
    """
    return Settings()
