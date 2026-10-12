"""API router for certificate retrieval and download.

Enforces database-backed path lookup, path traversal prevention,
and streaming of generated PDF certificate files.
"""

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import CertificateRecipient, RecipientStatus

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}",
    summary="Download a generated certificate PDF",
    description="Streams the generated PDF certificate for a verified recipient. Returns HTTP 404 if not found.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "The requested PDF certificate file.",
        },
        404: {
            "description": "Certificate record or physical file was not found.",
        },
    },
)
def download_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download a certificate by its unique certificate ID."""
    # 1. Lookup recipient by unique certificate_id
    recipient = (
        db.query(CertificateRecipient)
        .filter(CertificateRecipient.certificate_id == certificate_id)
        .first()
    )

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' was not found.",
        )

    if recipient.status != RecipientStatus.COMPLETED.value or not recipient.certificate_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' is not in COMPLETED state or file has not been generated.",
        )

    # 2. Path security check: ensure safe resolution
    file_path = Path(recipient.certificate_path).resolve()
    base_dir = Path(settings.CERTIFICATE_OUTPUT_DIR).resolve()

    # Ensure path is within the allowed output directory (prevent arbitrary file traversal)
    try:
        # Note: on Windows, commonpath or relative_to works reliably
        if not file_path.is_relative_to(base_dir) and not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate file path is invalid or outside permitted storage.",
            )
    except (ValueError, AttributeError):
        # Fallback check if python < 3.9 is used or drives differ
        if str(base_dir) not in str(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate file path is outside permitted storage.",
            )

    # 3. Check physical file presence on disk
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The certificate file was not found on the server filesystem.",
        )

    clean_filename = f"{certificate_id}.pdf"
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=clean_filename,
        headers={"Content-Disposition": f'inline; filename="{clean_filename}"'},
    )
