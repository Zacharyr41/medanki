from __future__ import annotations


class MedAnkiError(Exception):
    pass


class LLMError(MedAnkiError):
    pass


class ValidationError(MedAnkiError):
    pass


class IngestionError(MedAnkiError):
    pass
