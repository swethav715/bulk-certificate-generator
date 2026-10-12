"""Tests for input validation, schema constraints, and recipient-level validation."""

from fastapi.testclient import TestClient


def test_empty_recipients_list_rejected(client: TestClient):
    """Submitting an empty recipient list must return HTTP 422."""
    payload = {
        "event_name": "Docker Mastery",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-10",
        "organization_name": "Tech Corp",
        "recipients": [],
    }
    response = client.post("/api/v1/certificate-jobs", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("empty" in str(err).lower() for err in errors)


def test_missing_required_job_fields(client: TestClient):
    """Missing required top-level fields must return HTTP 422."""
    # Missing event_name
    payload_no_event = {
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-10",
        "organization_name": "Tech Corp",
        "recipients": [{"name": "A", "email": "a@example.com"}],
    }
    res = client.post("/api/v1/certificate-jobs", json=payload_no_event)
    assert res.status_code == 422

    # Missing organization_name
    payload_no_org = {
        "event_name": "Python Workshop",
        "completion_date": "2026-10-10",
        "recipients": [{"name": "A", "email": "a@example.com"}],
    }
    res2 = client.post("/api/v1/certificate-jobs", json=payload_no_org)
    assert res2.status_code == 422


def test_whitespace_job_fields(client: TestClient):
    """Whitespace-only fields must be rejected with HTTP 422."""
    payload = {
        "event_name": "   ",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-10",
        "organization_name": "   ",
        "recipients": [{"name": "A", "email": "a@example.com"}],
    }
    res = client.post("/api/v1/certificate-jobs", json=payload)
    assert res.status_code == 422


def test_invalid_date_format(client: TestClient):
    """Invalid completion date string must return HTTP 422."""
    payload = {
        "event_name": "Python Workshop",
        "certificate_title": "Certificate of Completion",
        "completion_date": "invalid-date-string",
        "organization_name": "Tech Corp",
        "recipients": [{"name": "A", "email": "a@example.com"}],
    }
    res = client.post("/api/v1/certificate-jobs", json=payload)
    assert res.status_code == 422


def test_batch_size_limit_exceeded(client: TestClient):
    """Batch size exceeding 500 must return HTTP 422."""
    recipients = [{"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(501)]
    payload = {
        "event_name": "Mega Conference",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-10",
        "organization_name": "Tech Corp",
        "recipients": recipients,
    }
    res = client.post("/api/v1/certificate-jobs", json=payload)
    assert res.status_code == 422
    assert "exceeds the maximum" in str(res.json()["detail"])


def test_recipient_level_validation_failures(client: TestClient):
    """Test recipient-level validation: invalid email, whitespace name, and duplicate emails.

    Policy:
    The job is accepted (HTTP 202). Invalid recipients are recorded as FAILED with
    clear error messages while valid recipients succeed. Job finishes with COMPLETED_WITH_ERRORS.
    """
    payload = {
        "event_name": "Data Science Summit",
        "certificate_title": "Certificate of Achievement",
        "completion_date": "2026-10-11",
        "organization_name": "Analytics Institute",
        "recipients": [
            {"name": "Valid Recipient", "email": "valid@example.com"},
            {"name": "   ", "email": "whitespace_name@example.com"},
            {"name": "Bad Email Recipient", "email": "not-a-valid-email"},
            {"name": "Duplicate Recipient", "email": "valid@example.com"},  # duplicate email!
        ],
    }

    create_res = client.post("/api/v1/certificate-jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # Check job status
    status_res = client.get(f"/api/v1/certificate-jobs/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()

    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["total_recipients"] == 4
    assert data["successful_count"] == 1
    assert data["failed_count"] == 3
    assert data["pending_count"] == 0
    assert data["progress_percentage"] == 100.0

    recipients = data["recipients"]
    # 1. Valid recipient succeeded
    assert recipients[0]["name"] == "Valid Recipient"
    assert recipients[0]["status"] == "COMPLETED"
    assert recipients[0]["certificate_id"] is not None

    # 2. Whitespace name failed
    assert recipients[1]["status"] == "FAILED"
    assert "whitespace" in recipients[1]["error_message"].lower()

    # 3. Bad email failed
    assert recipients[2]["status"] == "FAILED"
    assert "invalid recipient email" in recipients[2]["error_message"].lower()

    # 4. Duplicate email failed
    assert recipients[3]["status"] == "FAILED"
    assert "duplicate recipient email" in recipients[3]["error_message"].lower()
