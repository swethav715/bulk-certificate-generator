"""Live verification script demonstrating complete end-to-end flow.

1. Performs health check.
2. Creates a bulk certificate generation job with valid, whitespace, and duplicate recipients.
3. Inspects real-time job status, progress percentage, and recipient outcomes.
4. Downloads the generated PDF certificate and confirms file integrity.
"""

import json
from fastapi.testclient import TestClient

from app.main import app


def main():
    print("=== Bulk Certificate Generator Live Verification ===")
    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    print(f"[1] Health Check: HTTP {res.status_code} -> {res.json()}")
    assert res.status_code == 200

    # 2. Bulk Job Submission
    payload = {
        "event_name": "Full Stack Python Masterclass",
        "certificate_title": "Certificate of Excellence",
        "completion_date": "2026-10-12",
        "organization_name": "Antigravity Engineering",
        "recipients": [
            {"name": "Arun Kumar", "email": "arun@example.com", "extra_info": "High Distinction"},
            {"name": "Priya Sharma", "email": "priya@example.com", "extra_info": "Honors"},
            {"name": "   ", "email": "whitespace_name@example.com"},
            {"name": "Duplicate User", "email": "arun@example.com"},
        ],
    }

    create_res = client.post("/api/v1/certificate-jobs", json=payload)
    print(f"\n[2] Job Submission: HTTP {create_res.status_code}")
    job_info = create_res.json()
    print(json.dumps(job_info, indent=2))
    assert create_res.status_code == 202
    job_id = job_info["job_id"]

    # 3. Check Job Status
    status_res = client.get(f"/api/v1/certificate-jobs/{job_id}")
    print(f"\n[3] Job Status Query: HTTP {status_res.status_code}")
    status_data = status_res.json()
    print(f"Overall Status: {status_data['status']}")
    print(f"Total: {status_data['total_recipients']}")
    print(f"Successful: {status_data['successful_count']}")
    print(f"Failed: {status_data['failed_count']}")
    print(f"Progress Percentage: {status_data['progress_percentage']}%")

    print("\nRecipient Breakdown:")
    for r in status_data["recipients"]:
        print(
            f"  - Recipient ID: {r['id']} | Name: '{r['name']}' | Status: {r['status']} | "
            f"Cert ID: {r.get('certificate_id')} | Download URL: {r.get('download_url')} | "
            f"Error: {r.get('error_message')}"
        )

    assert status_data["status"] == "COMPLETED_WITH_ERRORS"
    assert status_data["successful_count"] == 2
    assert status_data["failed_count"] == 2

    # 4. Download Generated Certificate
    completed_recipients = [r for r in status_data["recipients"] if r["status"] == "COMPLETED"]
    assert len(completed_recipients) > 0
    first_cert_id = completed_recipients[0]["certificate_id"]

    dl_res = client.get(f"/api/v1/certificates/{first_cert_id}")
    print(f"\n[4] Download Certificate ({first_cert_id}): HTTP {dl_res.status_code}")
    print(f"Content-Type: {dl_res.headers.get('content-type')}")
    print(f"File Size: {len(dl_res.content)} bytes")
    assert dl_res.status_code == 200
    assert dl_res.content.startswith(b"%PDF-")

    # 5. List Generated Certificates for Job
    list_certs_res = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates")
    print(f"\n[5] List Job Certificates: HTTP {list_certs_res.status_code}")
    print(json.dumps(list_certs_res.json(), indent=2))
    assert list_certs_res.status_code == 200
    assert len(list_certs_res.json()) == 2

    print("\n>>> ALL VERIFICATION STEPS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    main()
