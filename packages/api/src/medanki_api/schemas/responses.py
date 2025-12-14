"""Response schemas for API endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Possible states for a processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadResponse(BaseModel):
    """Response model for single file upload."""

    job_id: str = Field(..., description="Unique identifier for the processing job")
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="Initial status of the job",
    )
    created_at: datetime = Field(..., description="Timestamp when job was created")


class MultiUploadResponse(BaseModel):
    """Response model for multiple file upload."""

    job_ids: list[str] = Field(
        ..., description="List of unique identifiers for the processing jobs"
    )
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="Initial status of the jobs",
    )
    created_at: datetime = Field(..., description="Timestamp when jobs were created")


class JobResponse(BaseModel):
    """Response model for job status."""

    id: str = Field(..., description="Unique identifier for the job")
    status: JobStatus = Field(..., description="Current status of the job")
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Processing progress percentage (0-100)",
    )
    filename: str | None = Field(default=None, description="Original filename")
    exam: str | None = Field(default=None, description="Target exam type")
    cards_generated: int = Field(
        default=0,
        description="Number of cards generated so far",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if job failed",
    )
    created_at: datetime = Field(..., description="Timestamp when job was created")
    updated_at: datetime = Field(..., description="Timestamp of last update")


class JobListResponse(BaseModel):
    """Response model for job listing."""

    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs matching the query")
    limit: int = Field(..., description="Maximum number of jobs returned")
    offset: int = Field(..., description="Number of jobs skipped")


class CancelJobResponse(BaseModel):
    """Response model for job cancellation."""

    id: str = Field(..., description="Unique identifier for the cancelled job")
    status: JobStatus = Field(
        default=JobStatus.CANCELLED,
        description="Status after cancellation",
    )
    cancelled: bool = Field(default=True, description="Indicates successful cancellation")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Human-readable error message")
    code: str | None = Field(
        default=None,
        description="Machine-readable error code",
    )
