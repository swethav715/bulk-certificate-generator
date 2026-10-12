"""Tests for failure handling, partial job failures, mock exceptions, and error isolation."""

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.services.certificate_generator import CertificateGenerationError


def test_simulated_pdf_generation_failure_isolation(client: TestClient):
    """Simulate a PDF generation failure for one recipient and verify others succeed.

    Verifies:
    1. A failure for one recipient does NOT halt processing of subsequent recipients.
    2. Recipient outcomes and error messages are recorded accurately.
    3. Final job status is COMPLETED_WITH_ERRORS.
    4. Successful and failed counts match expectations.
    """
    original_create = __import__(
        "app.services.job_processor", fromlist=["create_certificate"]
    ).create_certificate

    call_count = 0

    def mock_create_certificate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Fail on recipient #2 ("Failing Recipient")
        if kwargs.get("recipient_name") == "Failing Recipient":
            raise CertificateGenerationError("Disk write I/O error simulated during PDF creation")
        return original_create(*args, **kwargs)

    payload = {
        "event_name": "Resilience in Distributed Systems",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-12",
        "organization_name": "Robust Systems Ltd",
        "recipients": [
            {"name": "First Recipient", "email": "first@example.com"},
            {"name": "Failing Recipient", "email": "fail@example.com"},
            {"name": "Third Recipient", "email": "third@example.com"},
        ],
    }

    with patch("app.services.job_processor.create_certificate", side_effect=mock_create_certificate):
        res = client.post("/api/v1/certificate-jobs", json=payload)
        assert res.status_code == 202
        job_id = res.json()["job_id"]

    # Verify status
    status_res = client.get(f"/api/v1/certificate-jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()

    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["total_recipients"] == 3
    assert data["successful_count"] == 2
    assert data["failed_count"] == 1
    assert data["pending_count"] == 0
    assert data["progress_percentage"] == 100.0

    recipients = data["recipients"]
    # First succeeded
    assert recipients[0]["name"] == "First Recipient"
    assert recipients[0]["status"] == "COMPLETED"
    assert recipients[0]["certificate_id"] is not None

    # Second failed
    assert recipients[1]["name"] == "Failing Recipient"
    assert recipients[1]["status"] == "FAILED"
    assert recipients[1]["certificate_id"] is None
    assert "Disk write I/O error" in recipients[1]["error_message"]

    # Third succeeded despite second's failure!
    assert recipients[2]["name"] == "Third Recipient"
    assert recipients[2]["status"] == "COMPLETED"
    assert recipients[2]["certificate_id"] is not None


def test_job_with_all_recipients_failing(client: TestClient):
    """When all recipients fail, the final job status must be FAILED."""
    def mock_always_fail(*args, **kwargs):
        raise CertificateGenerationError("Renderer system unavailable")

    payload = {
        "event_name": "Failure Testing",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-12",
        "organization_name": "Test Org",
        "recipients": [
            {"name": "User One", "email": "one@example.com"},
            {"name": "User Two", "email": "two@example.com"},
        ],
    }

    with patch("app.services.job_processor.create_certificate", side_effect=mock_always_fail):
        res = client.post("/api/v1/certificate-jobs", json=payload)
        assert res.status_code == 202
        job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/certificate-jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()

    assert data["status"] == "FAILED"
    assert data["total_recipients"] == 2
    assert data["successful_count"] == 0
    assert data["failed_count"] == 2
    assert data["progress_percentage"] == 100.0
