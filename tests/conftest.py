import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from dataclasses import dataclass


@dataclass
class MedicalChunk:
    id: str
    content: str
    embedding: list[float]
    document_id: str
    exam_type: str | None = None
    metadata: dict | None = None


@pytest.fixture
def mock_weaviate_client():
    client = MagicMock()
    client.is_ready.return_value = True
    client.collections.exists.return_value = True

    collection = MagicMock()
    client.collections.get.return_value = collection

    return client


@pytest.fixture
def sample_chunk():
    return MedicalChunk(
        id=str(uuid4()),
        content="Congestive heart failure (CHF) is a chronic condition where the heart cannot pump blood effectively.",
        embedding=[0.1] * 384,
        document_id="doc_001",
        exam_type="USMLE",
        metadata={"page": 1, "source": "cardiology_textbook.pdf"}
    )


@pytest.fixture
def sample_chunks_with_embeddings():
    return [
        MedicalChunk(
            id=str(uuid4()),
            content="Congestive heart failure (CHF) is a chronic condition where the heart cannot pump blood effectively.",
            embedding=[0.1] * 384,
            document_id="doc_001",
            exam_type="USMLE",
            metadata={"page": 1}
        ),
        MedicalChunk(
            id=str(uuid4()),
            content="Treatment of CHF includes ACE inhibitors, beta blockers, and diuretics.",
            embedding=[0.2] * 384,
            document_id="doc_001",
            exam_type="USMLE",
            metadata={"page": 2}
        ),
        MedicalChunk(
            id=str(uuid4()),
            content="Diabetes mellitus type 2 is characterized by insulin resistance and relative insulin deficiency.",
            embedding=[0.3] * 384,
            document_id="doc_002",
            exam_type="COMLEX",
            metadata={"page": 1}
        ),
        MedicalChunk(
            id=str(uuid4()),
            content="Hypertension is defined as systolic BP >= 130 mmHg or diastolic BP >= 80 mmHg.",
            embedding=[0.4] * 384,
            document_id="doc_003",
            exam_type="USMLE",
            metadata={"page": 1}
        ),
        MedicalChunk(
            id=str(uuid4()),
            content="Acute myocardial infarction presents with chest pain, diaphoresis, and ECG changes.",
            embedding=[0.5] * 384,
            document_id="doc_001",
            exam_type="USMLE",
            metadata={"page": 5}
        ),
    ]
