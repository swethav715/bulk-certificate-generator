"""Background job processing service.

Handles asynchronous execution of certificate generation jobs, isolating
individual recipient errors and updating job lifecycle states safely.
"""

from datetime import datetime, timezone
import logging
from typing import Set

from app.database import SessionLocal
from app.models import CertificateJob, CertificateRecipient, JobStatus, RecipientStatus
from app.schemas import EMAIL_REGEX
from app.services.certificate_generator import create_certificate

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


def process_certificate_job(job_id: str) -> None:
    """Process all recipients for a bulk certificate generation job.

    This function is executed as an in-process background task (FastAPI BackgroundTasks).
    It manages its own database session to ensure thread safety.
    
    Failure Isolation Policy:
    - Each recipient is processed in an independent try-except block.
    - Recipient-level validation failures (empty name, invalid email, duplicate emails in batch)
      are recorded on the individual recipient record.
    - A failure for one recipient never stops remaining recipients from being processed.
    - The final job status accurately reflects outcomes (COMPLETED, COMPLETED_WITH_ERRORS, or FAILED).
    """
    db = SessionLocal()
    try:
        job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
        if not job:
            logger.error("Job %s not found in database during background execution", job_id)
            return

        # 1. Update job to PROCESSING state
        job.status = JobStatus.PROCESSING.value
        job.started_at = utc_now()
        db.commit()

        # Fetch all recipients for this job
        recipients = (
            db.query(CertificateRecipient)
            .filter(CertificateRecipient.job_id == job_id)
            .order_by(CertificateRecipient.id)
            .all()
        )

        seen_emails: Set[str] = set()

        for recipient in recipients:
            try:
                recipient.status = RecipientStatus.PROCESSING.value
                db.commit()

                # --- Recipient Validation ---
                # Check empty or whitespace name
                clean_name = recipient.name.strip() if recipient.name else ""
                if not clean_name:
                    recipient.status = RecipientStatus.FAILED.value
                    recipient.error_message = "Recipient name cannot be empty or contain only whitespace."
                    recipient.completed_at = utc_now()
                    job.failed_count += 1
                    db.commit()
                    continue

                # Check valid email format
                clean_email = recipient.email.strip() if recipient.email else ""
                if not EMAIL_REGEX.match(clean_email):
                    recipient.status = RecipientStatus.FAILED.value
                    recipient.error_message = f"Invalid recipient email address format: '{recipient.email}'"
                    recipient.completed_at = utc_now()
                    job.failed_count += 1
                    db.commit()
                    continue

                # Check duplicate email within the same batch
                norm_email = clean_email.lower()
                if norm_email in seen_emails:
                    recipient.status = RecipientStatus.FAILED.value
                    recipient.error_message = (
                        f"Duplicate recipient email within the same job batch: '{recipient.email}'"
                    )
                    recipient.completed_at = utc_now()
                    job.failed_count += 1
                    db.commit()
                    continue

                seen_emails.add(norm_email)

                # --- PDF Generation ---
                cert_id, cert_path = create_certificate(
                    recipient_name=clean_name,
                    event_name=job.event_name,
                    completion_date=job.completion_date,
                    organization_name=job.organization_name,
                    certificate_title=job.certificate_title,
                )

                # Mark recipient as COMPLETED
                recipient.certificate_id = cert_id
                recipient.certificate_path = cert_path
                recipient.status = RecipientStatus.COMPLETED.value
                recipient.error_message = None
                recipient.completed_at = utc_now()
                job.successful_count += 1
                db.commit()

            except Exception as exc:
                logger.warning(
                    "Error processing recipient %s (%s) in job %s: %s",
                    recipient.id,
                    recipient.email,
                    job_id,
                    str(exc),
                )
                db.rollback()  # Rollback any partial transaction
                recipient.status = RecipientStatus.FAILED.value
                # Record a safe error message without exposing internal stack traces
                recipient.error_message = f"Certificate generation failed: {str(exc)}"
                recipient.completed_at = utc_now()
                job.failed_count += 1
                db.commit()

        # --- Final Job Status Resolution ---
        total = job.total_recipients
        success = job.successful_count
        failed = job.failed_count

        if success == total and total > 0:
            job.status = JobStatus.COMPLETED.value
        elif success > 0 and failed > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
        elif failed == total and total > 0:
            job.status = JobStatus.FAILED.value
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value

        job.completed_at = utc_now()
        db.commit()
        logger.info(
            "Job %s finished with status %s (success=%s, failed=%s, total=%s)",
            job_id,
            job.status,
            success,
            failed,
            total,
        )

    except Exception as exc:
        logger.exception("Catastrophic error in job processing worker for job %s: %s", job_id, str(exc))
        try:
            job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.completed_at = utc_now()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
