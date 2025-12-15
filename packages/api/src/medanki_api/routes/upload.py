"""File upload API routes."""

from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from medanki_api.schemas.requests import ExamType
from medanki_api.schemas.responses import (
    JobStatus,
    MultiUploadResponse,
    UploadResponse,
)

router = APIRouter(prefix="/api", tags=["upload"])

# Allowed MIME types for upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/markdown",
    "text/plain",
    "text/x-markdown",
    "application/octet-stream",  # Sometimes used for .md files
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}

# Maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def _validate_file_type(file: UploadFile) -> None:
    """Validate that the uploaded file has an allowed type.

    Args:
        file: The uploaded file to validate.

    Raises:
        HTTPException: If the file type is not supported.
    """
    filename = file.filename or ""
    extension = ""
    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()

    content_type = file.content_type or ""

    # Check extension first
    if extension and extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {extension}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # If no extension, fall back to MIME type check
    if not extension and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {content_type}",
        )


async def _validate_file_size(file: UploadFile) -> bytes:
    """Validate file size and return content.

    Args:
        file: The uploaded file to validate.

    Returns:
        The file content as bytes.

    Raises:
        HTTPException: If the file exceeds the size limit.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )
    return content


def _validate_exam_type(exam: str | None) -> ExamType | None:
    """Validate exam type parameter.

    Args:
        exam: The exam type string to validate.

    Returns:
        The validated ExamType or None.

    Raises:
        HTTPException: If the exam type is invalid.
    """
    if exam is None:
        return None
    try:
        return ExamType(exam)
    except ValueError:
        valid_exams = [e.value for e in ExamType]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid exam type: {exam}. Valid options: {', '.join(valid_exams)}",
        ) from None


def _create_job(
    request: Request,
    filename: str,
    exam: ExamType | None,
    card_types: str | None,
    max_cards: int | None,
    file_path: str | None = None,
) -> dict:
    """Create a new job and store it in app state.

    Args:
        request: The FastAPI request object.
        filename: Original filename.
        exam: Target exam type.
        card_types: Comma-separated card types.
        max_cards: Maximum cards to generate.

    Returns:
        The created job dictionary.
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    job = {
        "id": job_id,
        "status": JobStatus.PENDING.value,
        "progress": 0.0,
        "filename": filename,
        "exam": exam.value if exam else None,
        "card_types": card_types,
        "max_cards": max_cards,
        "cards_generated": 0,
        "error_message": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "file_path": file_path,
        "cards": [],
    }

    # Store in app state
    if not hasattr(request.app.state, "job_storage"):
        request.app.state.job_storage = {}
    request.app.state.job_storage[job_id] = job

    return job


@router.post(
    "/upload",
    response_model=UploadResponse | MultiUploadResponse,
    responses={
        400: {"description": "Bad request - no file provided"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        422: {"description": "Validation error"},
    },
)
async def upload_file(
    request: Request,
    file: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    exam: Annotated[str | None, Form()] = None,
    card_types: Annotated[str | None, Form()] = None,
    max_cards: Annotated[int | None, Form()] = None,
) -> UploadResponse | MultiUploadResponse:
    """Upload one or more files for flashcard generation.

    Args:
        request: The FastAPI request object.
        file: Single file upload.
        files: Multiple files upload.
        exam: Target exam type (MCAT, USMLE_STEP1, USMLE_STEP2).
        card_types: Comma-separated list of card types.
        max_cards: Maximum number of cards to generate.

    Returns:
        UploadResponse for single file, MultiUploadResponse for multiple files.

    Raises:
        HTTPException: For validation errors.
    """
    # Validate exam type if provided
    validated_exam = _validate_exam_type(exam)

    # Handle multiple files
    if files and len(files) > 0:
        # Filter out empty files (happens with some clients)
        valid_files = [f for f in files if f.filename]
        if not valid_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files provided",
            )

        job_ids = []
        now = datetime.now(UTC)

        for upload_file in valid_files:
            _validate_file_type(upload_file)
            await _validate_file_size(upload_file)
            job = _create_job(
                request,
                upload_file.filename or "unknown",
                validated_exam,
                card_types,
                max_cards,
            )
            job_ids.append(job["id"])

        return MultiUploadResponse(
            job_ids=job_ids,
            status=JobStatus.PENDING,
            created_at=now,
        )

    # Handle single file
    if file is None or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    _validate_file_type(file)
    content = await _validate_file_size(file)

    # Save file to temp location
    suffix = Path(file.filename).suffix
    temp_dir = Path(tempfile.gettempdir()) / "medanki_uploads"
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / f"{uuid.uuid4()}{suffix}"
    temp_file.write_bytes(content)

    job = _create_job(
        request,
        file.filename,
        validated_exam,
        card_types,
        max_cards,
        file_path=str(temp_file),
    )

    return UploadResponse(
        job_id=job["id"],
        status=JobStatus.PENDING,
        created_at=datetime.fromisoformat(job["created_at"]),
    )
