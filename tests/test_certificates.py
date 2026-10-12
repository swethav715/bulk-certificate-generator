"""Tests for certificate generation, retrieval, and PDF download."""

from pathlib import Path
from fastapi.testclient import TestClient

from app.services.certificate_generator import create_certificate


def test_direct_pdf_generation(tmp_path: Path):
    """Test the standalone certificate generation function produces a valid PDF."""
    cert_id, file_path = create_certificate(
        recipient_name="Aditi Rao",
        event_name="Full Stack Web Bootcamp",
        completion_date="2026-10-15",
        organization_name="Global Learning Academy",
        output_directory=str(tmp_path),
    )

    assert cert_id.startswith("CERT-")
    pdf_file = Path(file_path)
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 0

    # Verify standard PDF header magic bytes (%PDF)
    with open(pdf_file, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_download_generated_certificate(client: TestClient):
    """Submit a job, retrieve certificate_id, and verify downloading the PDF via API."""
    payload = {
        "event_name": "Cloud Computing Essentials",
        "certificate_title": "Certificate of Excellence",
        "completion_date": "2026-10-12",
        "organization_name": "Tech Corp",
        "recipients": [
            {"name": "Sneha Patel", "email": "sneha@example.com"}
        ],
    }

    create_res = client.post("/api/v1/certificate-jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # Fetch job status to get certificate ID
    status_res = client.get(f"/api/v1/certificate-jobs/{job_id}")
    assert status_res.status_code == 200
    recipients = status_res.json()["recipients"]
    assert len(recipients) == 1
    cert_id = recipients[0]["certificate_id"]
    assert cert_id is not None

    # Download certificate PDF
    dl_res = client.get(f"/api/v1/certificates/{cert_id}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert dl_res.content.startswith(b"%PDF-")


def test_download_nonexistent_certificate(client: TestClient):
    """Attempting to download a nonexistent certificate ID returns 404."""
    dl_res = client.get("/api/v1/certificates/CERT-NONEXISTENT-999")
    assert dl_res.status_code == 404
    assert "not found" in dl_res.json()["detail"].lower()


def test_list_job_certificates(client: TestClient):
    """Verify endpoint to list all generated certificates for a job."""
    payload = {
        "event_name": "DevOps Intensive",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-12",
        "organization_name": "Cloud Academy",
        "recipients": [
            {"name": "Rahul Verma", "email": "rahul@example.com"},
            {"name": "Meera Joshi", "email": "meera@example.com"},
        ],
    }

    create_res = client.post("/api/v1/certificate-jobs", json=payload)
    job_id = create_res.json()["job_id"]

    # Query certificates for job
    certs_res = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    certs_data = certs_res.json()
    assert len(certs_data) == 2
    for item in certs_data:
        assert item["certificate_id"].startswith("CERT-")
        assert item["download_url"].startswith("/api/v1/certificates/")
