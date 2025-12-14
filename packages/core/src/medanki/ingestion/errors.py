"""Ingestion-related errors for MedAnki."""

from __future__ import annotations


class IngestionError(Exception):
    """Base exception for ingestion errors.

    Raised when file ingestion fails due to unsupported formats,
    corrupted files, or other extraction issues.
    """

    def __init__(self, message: str, path: str | None = None) -> None:
        """Initialize the error.

        Args:
            message: Error description.
            path: Optional file path that caused the error.
        """
        self.path = path
        super().__init__(message)
