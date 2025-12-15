"""Tests for file upload API endpoints."""

from __future__ import annotations

import io
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for the FastAPI app."""
    from medanki_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Create minimal valid PDF content for testing."""
    # Minimal PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [] /Count 0 >>
endobj
xref
0 3
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
trailer
<< /Size 3 /Root 1 0 R >>
startxref
109
%%EOF"""


@pytest.fixture
def sample_markdown_content() -> bytes:
    """Create sample markdown content for testing."""
    return b"""# Cardiovascular System

The heart is a muscular organ that pumps blood.

## Key Points
- Systole: contraction phase
- Diastole: relaxation phase
"""


class TestUploadPdfSuccess:
    """Test successful PDF upload."""

    async def test_upload_pdf_success(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """POST /api/upload with PDF returns job_id."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert isinstance(data["job_id"], str)
        assert len(data["job_id"]) > 0


class TestUploadMarkdownSuccess:
    """Test successful markdown upload."""

    async def test_upload_markdown_success(
        self, client: AsyncClient, sample_markdown_content: bytes
    ) -> None:
        """POST /api/upload with .md works."""
        files = {"file": ("notes.md", io.BytesIO(sample_markdown_content), "text/markdown")}

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestUploadMultipleFiles:
    """Test uploading multiple files in one request."""

    async def test_upload_multiple_files(
        self,
        client: AsyncClient,
        sample_pdf_content: bytes,
        sample_markdown_content: bytes,
    ) -> None:
        """Multiple files in one request creates multiple jobs."""
        files = [
            ("files", ("lecture1.pdf", io.BytesIO(sample_pdf_content), "application/pdf")),
            ("files", ("notes.md", io.BytesIO(sample_markdown_content), "text/markdown")),
        ]

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        # Should return list of job_ids for multiple files
        assert "job_ids" in data or "job_id" in data


class TestUploadRejectsUnsupported:
    """Test rejection of unsupported file types."""

    async def test_upload_rejects_unsupported(self, client: AsyncClient) -> None:
        """Uploading .xyz returns 415 Unsupported Media Type."""
        content = b"fake xyz content"
        files = {
            "file": (
                "document.xyz",
                io.BytesIO(content),
                "application/octet-stream",
            )
        }

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 415
        data = response.json()
        assert "detail" in data


class TestUploadRejectsTooLarge:
    """Test rejection of files exceeding size limit."""

    async def test_upload_rejects_too_large(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """Uploading >50MB returns 413 Payload Too Large."""
        # Create content larger than 50MB
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 413
        data = response.json()
        assert "detail" in data


class TestUploadRequiresFile:
    """Test that file is required."""

    async def test_upload_requires_file(self, client: AsyncClient) -> None:
        """Missing file returns 400 Bad Request."""
        response = await client.post("/api/upload")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestUploadAcceptsExamParam:
    """Test exam parameter handling."""

    async def test_upload_accepts_exam_param(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """exam=MCAT in form data is accepted."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        data = {"exam": "MCAT"}

        response = await client.post("/api/upload", files=files, data=data)

        assert response.status_code == 200
        result = response.json()
        assert "job_id" in result


class TestUploadAcceptsOptions:
    """Test card generation options."""

    async def test_upload_accepts_options(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """card_types and max_cards options are accepted."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        data = {
            "card_types": "cloze,vignette",
            "max_cards": "50",
        }

        response = await client.post("/api/upload", files=files, data=data)

        assert response.status_code == 200
        result = response.json()
        assert "job_id" in result


class TestUploadValidatesExam:
    """Test exam parameter validation."""

    async def test_upload_validates_exam(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """Invalid exam value returns 422 Unprocessable Entity."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        data = {"exam": "INVALID_EXAM"}

        response = await client.post("/api/upload", files=files, data=data)

        assert response.status_code == 422
        result = response.json()
        assert "detail" in result


class TestUploadReturnsJobId:
    """Test response includes job_id."""

    async def test_upload_returns_job_id(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """Response has job_id field."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert isinstance(data["job_id"], str)


class TestUploadReturnsStatus:
    """Test response includes status."""

    async def test_upload_returns_status(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """Response has status=pending."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "pending"


class TestUploadReturnsCreatedAt:
    """Test response includes timestamp."""

    async def test_upload_returns_created_at(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """Timestamp included in response."""
        files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}

        response = await client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        # Verify it's a valid ISO timestamp
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        assert isinstance(created_at, datetime)
