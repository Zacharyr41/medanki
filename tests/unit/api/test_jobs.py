"""Tests for job management API endpoints."""

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
async def created_job_id(client: AsyncClient, sample_pdf_content: bytes) -> str:
    """Create a job and return its ID."""
    files = {"file": ("lecture.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
    response = await client.post("/api/upload", files=files)
    return response.json()["job_id"]


class TestGetJobSuccess:
    """Test successful job retrieval."""

    async def test_get_job_success(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """GET /api/jobs/{id} returns job details."""
        response = await client.get(f"/api/jobs/{created_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_job_id


class TestGetJobNotFound:
    """Test job not found handling."""

    async def test_get_job_not_found(self, client: AsyncClient) -> None:
        """Unknown ID returns 404."""
        response = await client.get("/api/jobs/nonexistent-job-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestJobHasStatus:
    """Test job status field."""

    async def test_job_has_status(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """Response includes status field."""
        response = await client.get(f"/api/jobs/{created_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["pending", "processing", "completed", "failed", "cancelled"]


class TestJobHasProgress:
    """Test job progress field."""

    async def test_job_has_progress(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """Response includes progress 0-100."""
        response = await client.get(f"/api/jobs/{created_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "progress" in data
        assert isinstance(data["progress"], (int, float))
        assert 0 <= data["progress"] <= 100


class TestJobHasTimestamps:
    """Test job timestamp fields."""

    async def test_job_has_timestamps(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """Response includes created_at and updated_at fields."""
        response = await client.get(f"/api/jobs/{created_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data
        # Verify they're valid ISO timestamps
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        assert isinstance(created_at, datetime)
        assert isinstance(updated_at, datetime)


class TestListJobs:
    """Test job listing endpoint."""

    async def test_list_jobs(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """GET /api/jobs returns list of jobs."""
        response = await client.get("/api/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        # Should include the job we created
        job_ids = [job["id"] for job in data["jobs"]]
        assert created_job_id in job_ids


class TestListJobsPaginated:
    """Test job listing pagination."""

    async def test_list_jobs_paginated(
        self, client: AsyncClient, sample_pdf_content: bytes
    ) -> None:
        """Limit and offset parameters work for pagination."""
        # Create multiple jobs
        for i in range(3):
            files = {
                "file": (f"lecture{i}.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
            }
            await client.post("/api/upload", files=files)

        # Test pagination
        response = await client.get("/api/jobs", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) <= 2

        # Test offset
        response2 = await client.get("/api/jobs", params={"limit": 2, "offset": 1})
        assert response2.status_code == 200


class TestListJobsFiltered:
    """Test job listing filtering."""

    async def test_list_jobs_filtered(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """Filter by status works."""
        response = await client.get("/api/jobs", params={"status": "pending"})

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        # All returned jobs should have the filtered status
        for job in data["jobs"]:
            assert job["status"] == "pending"


class TestCancelJob:
    """Test job cancellation."""

    async def test_cancel_job(
        self, client: AsyncClient, created_job_id: str
    ) -> None:
        """DELETE /api/jobs/{id} cancels the job."""
        response = await client.delete(f"/api/jobs/{created_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "cancelled" or data.get("cancelled") is True

        # Verify the job is now cancelled
        verify_response = await client.get(f"/api/jobs/{created_job_id}")
        assert verify_response.json()["status"] == "cancelled"


class TestCancelCompletedFails:
    """Test that completed jobs cannot be cancelled."""

    async def test_cancel_completed_fails(self, client: AsyncClient) -> None:
        """Can't cancel finished job - returns error."""
        # Create a job
        pdf_content = b"""%PDF-1.4
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
        files = {"file": ("lecture.pdf", io.BytesIO(pdf_content), "application/pdf")}
        response = await client.post("/api/upload", files=files)
        job_id = response.json()["job_id"]

        # Mark job as completed (this would normally be done by a worker)
        # We need to use internal API or mock to set status to completed
        # For this test, we'll assume there's a way to complete a job
        # In the actual implementation, we'll use the database directly
        from medanki_api.main import app

        # Access the job storage and mark as completed
        if hasattr(app.state, "job_storage"):
            job = app.state.job_storage.get(job_id)
            if job:
                job["status"] = "completed"

        # Try to cancel the completed job
        response = await client.delete(f"/api/jobs/{job_id}")

        # Should fail because job is already completed
        assert response.status_code in [400, 409]  # Bad Request or Conflict
        data = response.json()
        assert "detail" in data
