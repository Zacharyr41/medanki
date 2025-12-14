"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path

# Test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "test_fixtures"


@pytest.fixture
def sample_pdf_path() -> Path:
    """Path to sample PDF for testing."""
    return TEST_DATA_DIR / "sample_lecture.pdf"


@pytest.fixture
def sample_text() -> str:
    """Sample medical text for testing."""
    return """
    Congestive heart failure (CHF) is a chronic progressive condition 
    that affects the pumping power of the heart muscles. The left ventricle 
    is unable to pump blood efficiently to meet the body's needs.
    
    Treatment includes ACE inhibitors such as lisinopril, beta-blockers 
    like metoprolol, and diuretics including furosemide.
    """


@pytest.fixture
def sample_chunk_text() -> str:
    """Sample chunk text for classification testing."""
    return """
    The cardiac cycle consists of two phases: systole and diastole.
    During systole, the ventricles contract and eject blood into the 
    aorta and pulmonary artery. The mitral and tricuspid valves close,
    producing the first heart sound (S1).
    """
