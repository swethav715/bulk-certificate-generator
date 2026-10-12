"""API router for certificate job operations.

Provides endpoints to submit bulk certificate jobs, monitor job progress,
list historical jobs with pagination, and query job-specific certificates.
"""

from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateJob, CertificateRecipient, JobStatus, RecipientStatus
from app.schemas import (
    CertificateJobCreate,
    JobCreateResponse,
    JobDetailResponse,
    JobListResponse,
    JobSummaryResponse,
    RecipientResponse,
    CertificateDetailResponse,
)
from app.services.job_processor import process_certificate_job

router = APIRouter(prefix="/certificate-jobs", tags=["Certificate Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a bulk certificate generation job",
    description="Accepts bulk recipient details, creates the job in QUEUED status, and initiates background processing.",
)
def create_certificate_job(
    payload: CertificateJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    """Create a new bulk certificate generation job and enqueue background generation."""
    # 1. Create CertificateJob record
    job = CertificateJob(
        event_name=payload.event_name,
        certificate_title=payload.certificate_title,
        completion_date=payload.completion_date,
        organization_name=payload.organization_name,
        status=JobStatus.QUEUED.value,
        total_recipients=len(payload.recipients),
        successful_count=0,
        failed_count=0,
    )
    db.add(job)
    db.flush()  # Generates job.id

    # 2. Pre-create individual CertificateRecipient records
    recipient_records = []
    for r in payload.recipients:
        rec_model = CertificateRecipient(
            job_id=job.id,
            name=r.name,
            email=r.email,
            status=RecipientStatus.PENDING.value,
        )
        recipient_records.append(rec_model)

    db.add_all(recipient_records)
    db.commit()
    db.refresh(job)

    # 3. Enqueue background processing task
    background_tasks.add_task(process_certificate_job, job.id)

    status_url = f"/api/v1/certificate-jobs/{job.id}"
    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        status_url=status_url,
        message="Bulk certificate generation job accepted and queued for processing.",
    )


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job status and progress",
    description="Returns overall job status, progress percentage, total/success/failed/pending counts, and recipient results.",
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobDetailResponse:
    """Retrieve the real-time status and detailed results for a specific bulk job."""
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    # Build recipient responses with download URLs for completed certificates
    recipient_responses: List[RecipientResponse] = []
    for r in job.recipients:
        dl_url = None
        if r.status == RecipientStatus.COMPLETED.value and r.certificate_id:
            dl_url = f"/api/v1/certificates/{r.certificate_id}"

        recipient_responses.append(
            RecipientResponse(
                id=r.id,
                name=r.name,
                email=r.email,
                status=r.status,
                certificate_id=r.certificate_id,
                download_url=dl_url,
                error_message=r.error_message,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
        )

    return JobDetailResponse(
        job_id=job.id,
        event_name=job.event_name,
        certificate_title=job.certificate_title,
        completion_date=job.completion_date,
        organization_name=job.organization_name,
        status=job.status,
        total_recipients=job.total_recipients,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        pending_count=job.pending_count,
        progress_percentage=job.progress_percentage,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        recipients=recipient_responses,
    )


@router.get(
    "",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all certificate jobs with pagination",
    description="Fetches a paginated list of certificate jobs ordered by creation time descending.",
)
def list_jobs(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """List jobs with pagination parameters limit and offset."""
    total = db.query(CertificateJob).count()
    jobs = (
        db.query(CertificateJob)
        .order_by(CertificateJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        JobSummaryResponse(
            id=j.id,
            event_name=j.event_name,
            certificate_title=j.certificate_title,
            organization_name=j.organization_name,
            status=j.status,
            total_recipients=j.total_recipients,
            successful_count=j.successful_count,
            failed_count=j.failed_count,
            pending_count=j.pending_count,
            progress_percentage=j.progress_percentage,
            created_at=j.created_at,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]

    return JobListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=List[CertificateDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List generated certificates for a job",
    description="Returns all successfully generated certificates belonging to the specified job.",
)
def list_job_certificates(
    job_id: str,
    db: Session = Depends(get_db),
) -> List[CertificateDetailResponse]:
    """Retrieve all successful certificates for a given job."""
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    completed_recipients = (
        db.query(CertificateRecipient)
        .filter(
            CertificateRecipient.job_id == job_id,
            CertificateRecipient.status == RecipientStatus.COMPLETED.value,
        )
        .all()
    )

    return [
        CertificateDetailResponse(
            certificate_id=r.certificate_id or "",
            recipient_name=r.name,
            recipient_email=r.email,
            event_name=job.event_name,
            organization_name=job.organization_name,
            completion_date=job.completion_date,
            download_url=f"/api/v1/certificates/{r.certificate_id}",
            issued_at=r.completed_at,
        )
        for r in completed_recipients
    ]
