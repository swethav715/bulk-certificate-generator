"""Pydantic schemas for request validation and response serialization.

Ensures strict typing, field constraints, date validation, and clear error messages.
"""

from datetime import date, datetime
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings

# Regular expression for RFC 5322 compliant basic email check
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class RecipientInput(BaseModel):
    """Input payload for a single certificate recipient."""
    name: str = Field(
        ...,
        description="Full recipient name as it should appear on the certificate",
        examples=["Arun Kumar"],
    )
    email: str = Field(
        ...,
        description="Recipient email address for delivery and verification",
        examples=["arun@example.com"],
    )
    extra_info: Optional[str] = Field(
        None,
        description="Optional certificate-specific details (e.g. grade, honors, seat)",
        examples=["Distinction"],
    )


class CertificateJobCreate(BaseModel):
    """Request payload to create a new bulk certificate generation job."""
    event_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the course, workshop, or event",
        examples=["Python Programming Workshop"],
    )
    certificate_title: str = Field(
        default="Certificate of Completion",
        min_length=1,
        max_length=255,
        description="Title heading of the certificate",
        examples=["Certificate of Completion"],
    )
    completion_date: str = Field(
        ...,
        description="Date of completion in ISO YYYY-MM-DD or display format",
        examples=["2026-10-10"],
    )
    organization_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the issuing organization",
        examples=["ABC Technologies"],
    )
    recipients: List[RecipientInput] = Field(
        ...,
        description="List of recipients to generate certificates for",
    )

    @field_validator("event_name", "certificate_title", "organization_name")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or only whitespace")
        return stripped

    @field_validator("completion_date")
    @classmethod
    def validate_completion_date(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Completion date cannot be empty")
        # Attempt to parse date format YYYY-MM-DD if matching format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", stripped):
            try:
                date.fromisoformat(stripped)
            except ValueError:
                raise ValueError("Invalid date string. Expected valid YYYY-MM-DD date.")
        elif not any(char.isdigit() for char in stripped):
            raise ValueError("Completion date must include a valid date or year")
        return stripped

    @field_validator("recipients")
    @classmethod
    def validate_recipients_batch(cls, v: List[RecipientInput]) -> List[RecipientInput]:
        if not v:
            raise ValueError("Recipients list cannot be empty. At least one recipient is required.")
        if len(v) > settings.MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size of {len(v)} exceeds the maximum allowed limit of {settings.MAX_BATCH_SIZE} recipients."
            )
        return v


class JobCreateResponse(BaseModel):
    """Response returned upon successfully queuing a bulk job (HTTP 202)."""
    job_id: str = Field(..., description="Unique identifier of the created job")
    status: str = Field(..., description="Initial job status (QUEUED)")
    total_recipients: int = Field(..., description="Total recipients queued")
    status_url: str = Field(..., description="URL to poll for job progress and results")
    message: str = Field(
        default="Bulk certificate generation job accepted and queued for processing."
    )


class RecipientResponse(BaseModel):
    """Detailed status and result for an individual recipient."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    status: str
    certificate_id: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class JobDetailResponse(BaseModel):
    """Comprehensive job status including counts, progress %, and recipient results."""
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    event_name: str
    certificate_title: str
    completion_date: str
    organization_name: str
    status: str
    total_recipients: int
    successful_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recipients: List[RecipientResponse] = []


class JobSummaryResponse(BaseModel):
    """Concise job summary used in paginated job listings."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    certificate_title: str
    organization_name: str
    status: str
    total_recipients: int
    successful_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    items: List[JobSummaryResponse]
    total: int
    limit: int
    offset: int


class CertificateDetailResponse(BaseModel):
    """Metadata for a successfully generated certificate."""
    certificate_id: str
    recipient_name: str
    recipient_email: str
    event_name: str
    organization_name: str
    completion_date: str
    download_url: str
    issued_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    app: str
    version: str
    timestamp: datetime
