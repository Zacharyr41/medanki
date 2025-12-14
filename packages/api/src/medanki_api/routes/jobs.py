"""Job management API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from medanki_api.schemas.responses import (
    CancelJobResponse,
    JobListResponse,
    JobResponse,
    JobStatus,
)

router = APIRouter(prefix="/api", tags=["jobs"])


def _get_job_storage(request: Request) -> dict:
    """Get the job storage from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        The job storage dictionary.
    """
    if not hasattr(request.app.state, "job_storage"):
        request.app.state.job_storage = {}
    return request.app.state.job_storage


def _get_job_or_404(request: Request, job_id: str) -> dict:
    """Get a job by ID or raise 404.

    Args:
        request: The FastAPI request object.
        job_id: The job ID to look up.

    Returns:
        The job dictionary.

    Raises:
        HTTPException: If the job is not found.
    """
    storage = _get_job_storage(request)
    if job_id not in storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )
    return storage[job_id]


def _job_to_response(job: dict) -> JobResponse:
    """Convert a job dictionary to a JobResponse.

    Args:
        job: The job dictionary.

    Returns:
        The JobResponse model.
    """
    return JobResponse(
        id=job["id"],
        status=JobStatus(job["status"]),
        progress=job["progress"],
        filename=job.get("filename"),
        exam=job.get("exam"),
        cards_generated=job.get("cards_generated", 0),
        error_message=job.get("error_message"),
        created_at=datetime.fromisoformat(job["created_at"]),
        updated_at=datetime.fromisoformat(job["updated_at"]),
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={
        404: {"description": "Job not found"},
    },
)
async def get_job(request: Request, job_id: str) -> JobResponse:
    """Get the status of a specific job.

    Args:
        request: The FastAPI request object.
        job_id: The ID of the job to retrieve.

    Returns:
        The job details.

    Raises:
        HTTPException: If the job is not found.
    """
    job = _get_job_or_404(request, job_id)
    return _job_to_response(job)


@router.get(
    "/jobs",
    response_model=JobListResponse,
)
async def list_jobs(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> JobListResponse:
    """List all jobs with optional filtering and pagination.

    Args:
        request: The FastAPI request object.
        limit: Maximum number of jobs to return.
        offset: Number of jobs to skip.
        status_filter: Filter by job status.

    Returns:
        The list of jobs with pagination info.
    """
    storage = _get_job_storage(request)
    jobs = list(storage.values())

    # Apply status filter if provided
    if status_filter:
        jobs = [j for j in jobs if j["status"] == status_filter]

    total = len(jobs)

    # Sort by created_at descending (newest first)
    jobs.sort(key=lambda j: j["created_at"], reverse=True)

    # Apply pagination
    paginated_jobs = jobs[offset : offset + limit]

    return JobListResponse(
        jobs=[_job_to_response(j) for j in paginated_jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/jobs/{job_id}",
    response_model=CancelJobResponse,
    responses={
        400: {"description": "Cannot cancel completed job"},
        404: {"description": "Job not found"},
        409: {"description": "Job cannot be cancelled in current state"},
    },
)
async def cancel_job(request: Request, job_id: str) -> CancelJobResponse:
    """Cancel a pending or processing job.

    Args:
        request: The FastAPI request object.
        job_id: The ID of the job to cancel.

    Returns:
        Confirmation of cancellation.

    Raises:
        HTTPException: If the job is not found or cannot be cancelled.
    """
    job = _get_job_or_404(request, job_id)

    current_status = JobStatus(job["status"])

    # Cannot cancel completed, failed, or already cancelled jobs
    if current_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {current_status.value}",
        )

    # Update the job status
    now = datetime.now(UTC)
    job["status"] = JobStatus.CANCELLED.value
    job["updated_at"] = now.isoformat()

    return CancelJobResponse(
        id=job_id,
        status=JobStatus.CANCELLED,
        cancelled=True,
    )
