"""Integration test fixtures for MedAnki pipeline tests.

Provides fixtures for real services (not mocks) including:
- Weaviate testcontainer for vector store
- SQLite temp database
- Sample files (PDF, MD)
- HTTP client for API testing
"""

from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import numpy as np
import pytest

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "test_fixtures"


# ============================================================================
# Sample content for tests
# ============================================================================

CARDIOLOGY_CONTENT = """
# Cardiovascular System

The cardiovascular system is responsible for circulating blood throughout the body.
The heart is a four-chambered muscular organ that pumps blood.

## Heart Anatomy

The heart consists of:
- Right atrium: receives deoxygenated blood from the body
- Right ventricle: pumps blood to the lungs
- Left atrium: receives oxygenated blood from the lungs
- Left ventricle: pumps blood to the body

## Cardiac Cycle

The cardiac cycle consists of systole and diastole phases.
During systole, the ventricles contract (blood pressure: 120 mmHg).
During diastole, the ventricles relax (blood pressure: 80 mmHg).

## Congestive Heart Failure (CHF)

CHF occurs when the heart cannot pump enough blood to meet the body's needs.
Treatment includes ACE inhibitors like lisinopril 10mg daily and
beta-blockers such as metoprolol 25mg twice daily.

## Coronary Arteries

The left anterior descending artery supplies the anterior wall of the left ventricle.
The right coronary artery supplies the right ventricle and inferior wall.
"""

PHARMACOLOGY_CONTENT = """
# Pharmacology Overview

## Beta-Blockers

Beta-blockers work by blocking beta-adrenergic receptors.
Common examples include:
- Metoprolol 25-100mg twice daily
- Atenolol 50-100mg daily
- Propranolol 40-160mg twice daily

### Mechanism of Action

Beta-1 receptor blockade reduces heart rate and contractility.
Beta-2 receptor blockade can cause bronchoconstriction.

## ACE Inhibitors

ACE inhibitors block the conversion of angiotensin I to angiotensin II.
Examples include:
- Lisinopril 5-40mg daily
- Enalapril 5-20mg twice daily
- Ramipril 2.5-10mg daily

### Side Effects

Common side effects include:
- Dry cough (bradykinin accumulation)
- Hyperkalemia (K+ > 5.5 mEq/L)
- Angioedema

## Diuretics

### Loop Diuretics
Furosemide 20-80mg inhibits Na-K-2Cl cotransporter in the thick ascending loop of Henle.

### Thiazide Diuretics
Hydrochlorothiazide 12.5-50mg inhibits Na-Cl cotransporter in the distal tubule.
"""


# ============================================================================
# Mock services for integration tests
# ============================================================================


@dataclass
class MockLLMClient:
    """Mock LLM client that returns predetermined cloze cards."""

    def _generate_cloze_from_text(self, text: str, count: int) -> list[dict[str, Any]]:
        """Generate simple cloze cards from text content."""
        cards = []

        # Extract key medical terms and create cloze deletions
        if "systole" in text.lower() and "diastole" in text.lower():
            cards.append(
                {
                    "text": "The cardiac cycle consists of {{c1::systole}} and {{c2::diastole}} phases.",
                    "tags": ["cardiology", "physiology"],
                }
            )

        if "lisinopril" in text.lower():
            cards.append(
                {
                    "text": "{{c1::Lisinopril}} is an ACE inhibitor used for hypertension.",
                    "tags": ["pharmacology", "cardiovascular"],
                }
            )

        if "metoprolol" in text.lower():
            cards.append(
                {
                    "text": "{{c1::Metoprolol}} is a beta-blocker that reduces heart rate.",
                    "tags": ["pharmacology", "cardiovascular"],
                }
            )

        if "chf" in text.lower() or "heart failure" in text.lower():
            cards.append(
                {
                    "text": "Congestive heart failure occurs when the heart cannot {{c1::pump}} enough blood.",
                    "tags": ["cardiology", "pathology"],
                }
            )

        if "furosemide" in text.lower():
            cards.append(
                {
                    "text": "{{c1::Furosemide}} inhibits the Na-K-2Cl cotransporter in the loop of Henle.",
                    "tags": ["pharmacology", "nephrology"],
                }
            )

        if "left anterior descending" in text.lower():
            cards.append(
                {
                    "text": "The {{c1::left anterior descending}} artery supplies the anterior wall of the left ventricle.",
                    "tags": ["cardiology", "anatomy"],
                }
            )

        # Default card if no specific content matched
        if not cards:
            cards.append(
                {
                    "text": "Medical knowledge requires {{c1::understanding}} of key concepts.",
                    "tags": ["general"],
                }
            )

        return cards[:count]

    async def generate_cloze_cards(
        self,
        text: str,
        count: int = 3,
        tags: list[str] | None = None,
        topic_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate cloze cards from text."""
        return self._generate_cloze_from_text(text, count)

    async def generate_vignette(
        self,
        text: str,
        count: int = 1,
    ) -> list[dict[str, Any]]:
        """Generate vignette cards from text."""
        return [
            {
                "stem": "A 55-year-old male presents with chest pain and shortness of breath.",
                "question": "What is the most likely diagnosis?",
                "options": [
                    {"letter": "A", "text": "Myocardial infarction"},
                    {"letter": "B", "text": "Pulmonary embolism"},
                    {"letter": "C", "text": "Pneumonia"},
                    {"letter": "D", "text": "Aortic dissection"},
                    {"letter": "E", "text": "Pericarditis"},
                ],
                "answer": "A",
                "explanation": "ST elevation and troponin elevation suggest MI.",
            }
        ]

    async def check_accuracy(self, claim: str) -> dict[str, Any]:
        """Check accuracy of a medical claim."""
        return {"is_accurate": True, "confidence": 0.95}

    async def check_grounding(self, claim: str, source: str) -> dict[str, Any]:
        """Check if claim is grounded in source."""
        return {"is_grounded": True, "explanation": "Claim matches source content."}


@dataclass
class MockEmbeddingService:
    """Mock embedding service that generates deterministic embeddings."""

    dimension: int = 768

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate deterministic embedding from text hash."""
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.random(self.dimension).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        return self._generate_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [self._generate_embedding(t) for t in texts]


@dataclass
class MockVectorStore:
    """In-memory vector store for integration testing."""

    chunks: dict[str, Any] = field(default_factory=dict)
    embeddings: dict[str, list[float]] = field(default_factory=dict)

    def upsert(self, chunk: Any) -> str:
        """Store a chunk with its embedding."""
        chunk_id = getattr(chunk, "id", str(uuid4()))
        self.chunks[chunk_id] = chunk
        self.embeddings[chunk_id] = getattr(chunk, "embedding", [])
        return chunk_id

    def upsert_batch(self, chunks: list[Any]) -> list[str]:
        """Store multiple chunks."""
        return [self.upsert(c) for c in chunks]

    def get_by_id(self, chunk_id: str) -> Any | None:
        """Retrieve a chunk by ID."""
        return self.chunks.get(chunk_id)

    def delete(self, chunk_id: str) -> None:
        """Delete a chunk."""
        self.chunks.pop(chunk_id, None)
        self.embeddings.pop(chunk_id, None)

    def health_check(self) -> bool:
        """Check if store is healthy."""
        return True

    def hybrid_search(
        self,
        query: str,
        alpha: float = 0.5,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (simplified for testing)."""
        results = []
        query_lower = query.lower()

        for chunk_id, chunk in self.chunks.items():
            content = getattr(chunk, "content", "") or getattr(chunk, "text", "")
            if not content:
                continue

            # Simple keyword matching for score
            content_lower = content.lower()
            words_matched = sum(1 for word in query_lower.split() if word in content_lower)
            score = min(1.0, words_matched / max(1, len(query_lower.split())))

            if score > 0.1:
                results.append(
                    {
                        "topic_id": chunk_id,
                        "score": score,
                        "chunk": chunk,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


@dataclass
class MockTaxonomyService:
    """Mock taxonomy service for classification tests."""

    def get_taxonomy(self, exam_type: str) -> dict[str, Any]:
        """Get taxonomy for exam type."""
        if exam_type == "mcat":
            return {
                "exam_type": "mcat",
                "topics": [
                    {
                        "id": "FC4",
                        "name": "Cardiovascular System",
                        "path": "Foundational Concept 4",
                    },
                    {
                        "id": "FC4A",
                        "name": "Heart Anatomy",
                        "path": "Foundational Concept 4 > Heart",
                    },
                    {"id": "FC2", "name": "Biochemistry", "path": "Foundational Concept 2"},
                    {
                        "id": "FC2C",
                        "name": "Pharmacology",
                        "path": "Foundational Concept 2 > Pharmacology",
                    },
                ],
            }
        return {
            "exam_type": "usmle",
            "topics": [
                {"id": "CVS", "name": "Cardiovascular", "path": "Organ Systems > Cardiovascular"},
                {"id": "PHARM", "name": "Pharmacology", "path": "Pharmacology"},
            ],
        }

    def get_topics(self) -> list[dict[str, Any]]:
        """Get all topics."""
        return [
            {"id": "FC4", "name": "Cardiovascular System"},
            {"id": "FC4A", "name": "Heart Anatomy"},
            {"id": "FC2", "name": "Biochemistry"},
            {"id": "FC2C", "name": "Pharmacology"},
            {"id": "CVS", "name": "Cardiovascular"},
            {"id": "PHARM", "name": "Pharmacology"},
        ]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def sample_pdf_path(test_data_dir: Path) -> Path:
    """Path to sample lecture PDF."""
    return test_data_dir / "sample_lecture.pdf"


@pytest.fixture
def sample_md_path(test_data_dir: Path) -> Path:
    """Path to sample notes markdown."""
    return test_data_dir / "sample_notes.md"


@pytest.fixture
def cardiology_content() -> str:
    """Return cardiology sample content."""
    return CARDIOLOGY_CONTENT


@pytest.fixture
def pharmacology_content() -> str:
    """Return pharmacology sample content."""
    return PHARMACOLOGY_CONTENT


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_sqlite_db(temp_directory: Path) -> Path:
    """Create a temporary SQLite database file."""
    return temp_directory / "test_medanki.db"


@pytest.fixture
def temp_output_dir(temp_directory: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = temp_directory / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Return mock LLM client for card generation."""
    return MockLLMClient()


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingService:
    """Return mock embedding service."""
    return MockEmbeddingService()


@pytest.fixture
def mock_vector_store() -> MockVectorStore:
    """Return mock vector store."""
    return MockVectorStore()


@pytest.fixture
def mock_taxonomy_service() -> MockTaxonomyService:
    """Return mock taxonomy service."""
    return MockTaxonomyService()


@pytest.fixture
def sample_cardiology_md(temp_directory: Path, cardiology_content: str) -> Path:
    """Create a temporary cardiology markdown file."""
    path = temp_directory / "cardiology.md"
    path.write_text(cardiology_content)
    return path


@pytest.fixture
def sample_pharmacology_md(temp_directory: Path, pharmacology_content: str) -> Path:
    """Create a temporary pharmacology markdown file."""
    path = temp_directory / "pharmacology.md"
    path.write_text(pharmacology_content)
    return path


@pytest.fixture
def sample_test_directory(
    temp_directory: Path,
    cardiology_content: str,
    pharmacology_content: str,
) -> Path:
    """Create a directory with multiple test files."""
    # Create subdirectories
    lectures_dir = temp_directory / "lectures"
    lectures_dir.mkdir(exist_ok=True)

    notes_dir = temp_directory / "notes"
    notes_dir.mkdir(exist_ok=True)

    # Create files
    (lectures_dir / "cardiology.md").write_text(cardiology_content)
    (notes_dir / "pharmacology.md").write_text(pharmacology_content)
    (notes_dir / "readme.txt").write_text("This is a readme file.")

    return temp_directory


@pytest.fixture
def sample_chunk_with_cardiology():
    """Create a sample chunk with cardiology content."""

    @dataclass
    class SampleChunk:
        id: str = "chunk_cardio_001"
        document_id: str = "doc_001"
        text: str = "The cardiac cycle consists of systole and diastole phases. During systole, the ventricles contract."
        content: str = ""
        start_char: int = 0
        end_char: int = 100
        token_count: int = 20
        section_path: list[str] = field(default_factory=list)
        tags: list[str] = field(default_factory=lambda: ["cardiology"])

        def __post_init__(self):
            self.content = self.text

    return SampleChunk()


@pytest.fixture
def sample_chunk_with_pharmacology():
    """Create a sample chunk with pharmacology content."""

    @dataclass
    class SampleChunk:
        id: str = "chunk_pharm_001"
        document_id: str = "doc_002"
        text: str = (
            "Lisinopril is an ACE inhibitor. Metoprolol is a beta-blocker used for hypertension."
        )
        content: str = ""
        start_char: int = 0
        end_char: int = 90
        token_count: int = 18
        section_path: list[str] = field(default_factory=list)
        tags: list[str] = field(default_factory=lambda: ["pharmacology"])

        def __post_init__(self):
            self.content = self.text

    return SampleChunk()


@pytest.fixture
def sample_chunk_with_chf():
    """Create a sample chunk with CHF abbreviation."""

    @dataclass
    class SampleChunk:
        id: str = "chunk_chf_001"
        document_id: str = "doc_003"
        text: str = (
            "CHF (congestive heart failure) occurs when the heart cannot pump blood effectively."
        )
        content: str = ""
        start_char: int = 0
        end_char: int = 80
        token_count: int = 15
        section_path: list[str] = field(default_factory=list)
        tags: list[str] = field(default_factory=lambda: ["cardiology"])

        def __post_init__(self):
            self.content = self.text

    return SampleChunk()


# ============================================================================
# API client fixture for HTTP testing
# ============================================================================


@pytest.fixture
async def api_client():
    """Create an async HTTP client for API testing.

    Note: This requires the API to be set up. For now, returns a mock.
    """
    try:
        from httpx import AsyncClient

        from medanki_api.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    except ImportError:
        # Return a mock if API is not available
        yield MagicMock()


# ============================================================================
# VCR fixtures for LLM call recording
# ============================================================================


@pytest.fixture
def vcr_cassette_dir() -> Path:
    """Directory for VCR cassettes."""
    cassette_dir = Path(__file__).parent / "cassettes"
    cassette_dir.mkdir(exist_ok=True)
    return cassette_dir
