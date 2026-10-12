"""Tests for bulk certificate jobs management and endpoints."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
    assert "timestamp" in data


def test_create_bulk_job_and_poll_status(client: TestClient):
    """Test submitting a valid bulk job and polling its status until completion."""
    payload = {
        "event_name": "Python Programming Workshop",
        "certificate_title": "Certificate of Completion",
        "completion_date": "2026-10-10",
        "organization_name": "ABC Technologies",
        "recipients": [
            {"name": "Arun Kumar", "email": "arun@example.com"},
            {"name": "Priya Sharma", "email": "priya@example.com"},
            {"name": "Karthik Raj", "email": "karthik@example.com"},
        ],
    }

    # 1. Create Job (HTTP 202 Accepted)
    response = client.post("/api/v1/certificate-jobs", json=payload)
    assert response.status_code == 202
    job_data = response.json()
    assert "job_id" in job_data
    assert job_data["total_recipients"] == 3
    assert job_data["status_url"] == f"/api/v1/certificate-jobs/{job_data['job_id']}"

    job_id = job_data["job_id"]

    # 2. Query Job Status (In TestClient, BackgroundTasks run during request processing)
    status_response = client.get(f"/api/v1/certificate-jobs/{job_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()

    assert status_data["job_id"] == job_id
    assert status_data["event_name"] == "Python Programming Workshop"
    assert status_data["organization_name"] == "ABC Technologies"
    assert status_data["status"] == "COMPLETED"
    assert status_data["total_recipients"] == 3
    assert status_data["successful_count"] == 3
    assert status_data["failed_count"] == 0
    assert status_data["pending_count"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert len(status_data["recipients"]) == 3

    # Verify each recipient has a certificate_id and download_url
    for rec in status_data["recipients"]:
        assert rec["status"] == "COMPLETED"
        assert rec["certificate_id"] is not None
        assert rec["download_url"] is not None
        assert rec["certificate_id"] in rec["download_url"]
        assert rec["error_message"] is None


def test_get_nonexistent_job(client: TestClient):
    """Verify that querying a nonexistent job ID returns HTTP 404."""
    response = client.get("/api/v1/certificate-jobs/nonexistent-uuid-12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_jobs_and_pagination(client: TestClient):
    """Test listing jobs with limit and offset pagination parameters."""
    # Submit 3 distinct jobs
    for i in range(3):
        payload = {
            "event_name": f"Event Batch {i}",
            "certificate_title": "Certificate of Completion",
            "completion_date": "2026-10-10",
            "organization_name": "ABC Tech",
            "recipients": [{"name": f"User {i}", "email": f"user{i}@example.com"}],
        }
        res = client.post("/api/v1/certificate-jobs", json=payload)
        assert res.status_code == 202

    # Query with limit 2, offset 0
    list_res = client.get("/api/v1/certificate-jobs?limit=2&offset=0")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2

    # Query next page with limit 2, offset 2
    page2_res = client.get("/api/v1/certificate-jobs?limit=2&offset=2")
    assert page2_res.status_code == 200
    page2_data = page2_res.json()
    assert page2_data["total"] == 3
    assert len(page2_data["items"]) == 1


def test_list_jobs_invalid_pagination(client: TestClient):
    """Verify validation on pagination parameters."""
    # Invalid limit (less than 1)
    res_low = client.get("/api/v1/certificate-jobs?limit=0")
    assert res_low.status_code == 422

    # Invalid limit (greater than 100)
    res_high = client.get("/api/v1/certificate-jobs?limit=101")
    assert res_high.status_code == 422

    # Negative offset
    res_neg = client.get("/api/v1/certificate-jobs?offset=-1")
    assert res_neg.status_code == 422
