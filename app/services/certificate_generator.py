"""Certificate generation service.

Coordinates unique certificate ID generation, output path management,
and calling the ReportLab rendering engine.
"""

from pathlib import Path
from typing import Optional
import uuid

from app.core.config import settings
from templates.certificate_template import generate_certificate_pdf


class CertificateGenerationError(Exception):
    """Custom exception raised when PDF certificate rendering or disk write fails."""
    pass


def generate_unique_certificate_id() -> str:
    """Generate a clean, professional, collisions-free certificate identifier."""
    random_part = uuid.uuid4().hex[:12].upper()
    return f"CERT-{random_part[:4]}-{random_part[4:8]}-{random_part[8:]}"


def create_certificate(
    recipient_name: str,
    event_name: str,
    completion_date: str,
    organization_name: str,
    certificate_title: str = "Certificate of Completion",
    extra_info: Optional[str] = None,
    output_directory: Optional[str] = None,
) -> tuple[str, str]:
    """Generate a certificate PDF and persist it to the output directory.

    Args:
        recipient_name: Name of recipient.
        event_name: Name of course or event.
        completion_date: Date of completion.
        organization_name: Issuing organization.
        certificate_title: Certificate heading.
        extra_info: Optional notes or distinctions.
        output_directory: Optional override directory for testing.

    Returns:
        tuple[str, str]: (certificate_id, relative_or_resolved_file_path)

    Raises:
        CertificateGenerationError: If PDF generation or writing fails.
    """
    try:
        cert_id = generate_unique_certificate_id()
        base_dir = Path(output_directory or settings.CERTIFICATE_OUTPUT_DIR)
        base_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{cert_id}.pdf"
        dest_path = base_dir / filename

        generate_certificate_pdf(
            file_path=str(dest_path),
            recipient_name=recipient_name,
            event_name=event_name,
            completion_date=completion_date,
            organization_name=organization_name,
            certificate_id=cert_id,
            certificate_title=certificate_title,
            extra_info=extra_info,
        )

        # Store normalized path
        return cert_id, str(dest_path.resolve())

    except Exception as exc:
        raise CertificateGenerationError(f"Failed to generate certificate: {str(exc)}") from exc
