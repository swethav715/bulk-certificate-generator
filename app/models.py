"""SQLAlchemy ORM models for jobs and recipients.

Defines the CertificateJob and CertificateRecipient tables with relationships,
indexes, and status tracking.
"""

from datetime import datetime, timezone
import enum
from typing import List, Optional
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


class JobStatus(str, enum.Enum):
    """Lifecycle statuses for a bulk certificate generation job."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class RecipientStatus(str, enum.Enum):
    """Lifecycle statuses for an individual certificate recipient."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class CertificateJob(Base):
    """Represents a bulk certificate generation job submitted by a client."""
    __tablename__ = "certificate_jobs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        doc="Unique UUID identifier for the bulk job",
    )
    event_name = Column(String(255), nullable=False, doc="Event or course name")
    certificate_title = Column(
        String(255),
        nullable=False,
        default="Certificate of Completion",
        doc="Title displayed on the certificate",
    )
    completion_date = Column(
        String(50),
        nullable=False,
        doc="Date string of completion (e.g., '2026-10-10')",
    )
    organization_name = Column(
        String(255),
        nullable=False,
        doc="Issuing organization or institution name",
    )
    status = Column(
        String(50),
        nullable=False,
        default=JobStatus.QUEUED.value,
        index=True,
        doc="Current job status",
    )
    total_recipients = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of recipients in the job",
    )
    successful_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of successfully generated certificates",
    )
    failed_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of recipients that failed validation or PDF generation",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        doc="Timestamp when the job was submitted",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when background processing began",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when job processing finished",
    )

    # Relationships
    recipients = relationship(
        "CertificateRecipient",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CertificateRecipient.id",
    )

    @property
    def pending_count(self) -> int:
        """Calculate count of recipients still pending or in progress."""
        return max(0, self.total_recipients - (self.successful_count + self.failed_count))

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage safely avoiding division by zero."""
        if self.total_recipients <= 0:
            return 0.0
        finished = self.successful_count + self.failed_count
        return round((finished / self.total_recipients) * 100.0, 2)


class CertificateRecipient(Base):
    """Represents an individual recipient within a bulk certificate job."""
    __tablename__ = "certificate_recipients"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Primary auto-incrementing recipient record ID",
    )
    job_id = Column(
        String(36),
        ForeignKey("certificate_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the parent certificate job",
    )
    name = Column(String(255), nullable=False, doc="Full name of recipient")
    email = Column(String(255), nullable=False, index=True, doc="Recipient email address")
    status = Column(
        String(50),
        nullable=False,
        default=RecipientStatus.PENDING.value,
        index=True,
        doc="Status of this recipient's certificate generation",
    )
    certificate_id = Column(
        String(64),
        unique=True,
        index=True,
        nullable=True,
        doc="Globally unique certificate verification identifier",
    )
    certificate_path = Column(
        String(500),
        nullable=True,
        doc="Relative filesystem path to the generated certificate PDF",
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Sanitized error description if generation or validation failed",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        doc="Timestamp when record was queued",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when generation finished or failed",
    )

    # Relationship back to job
    job = relationship("CertificateJob", back_populates="recipients")

    # Composite index for querying recipients by job and status
    __table_args__ = (
        Index("ix_job_id_status", "job_id", "status"),
    )
