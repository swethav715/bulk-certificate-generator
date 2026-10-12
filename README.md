# Bulk Certificate Generator API

A production-minded, developer-friendly REST API built with **FastAPI**, **SQLite**, **SQLAlchemy**, and **ReportLab** that accepts bulk certificate generation requests, validates recipient lists, renders personalized landscape PDF certificates using a predefined template, tracks asynchronous job progression, and serves generated certificates securely.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Setup & Installation (Windows & VS Code)](#setup--installation-windows--vs-code)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [Interactive API Documentation](#interactive-api-documentation)
- [Running the Test Suite](#running-the-test-suite)
- [API Reference & Examples](#api-reference--examples)
  - [1. Health Check](#1-health-check)
  - [2. Create Bulk Certificate Job](#2-create-bulk-certificate-job)
  - [3. Check Job Status & Progress](#3-check-job-status--progress)
  - [4. List Jobs (Paginated)](#4-list-jobs-paginated)
  - [5. Download Certificate PDF](#5-download-certificate-pdf)
  - [6. List Certificates for Job](#6-list-certificates-for-job)
- [Database Schema](#database-schema)
- [Certificate Storage & Security](#certificate-storage--security)
- [Design Decisions](#design-decisions)
- [Background Processing & Limitations](#background-processing--limitations)
- [Future Improvements](#future-improvements)

---

## Project Overview

Organizations regularly issue completion certificates in bulk for workshops, webinars, bootcamps, and employee training. Generating hundreds of PDFs synchronously within a single web request causes timeouts, gateway errors, and memory spikes.

This project solves this by:
1. Instantly acknowledging bulk submissions with **HTTP 202 Accepted** and a tracking identifier.
2. Generating certificates asynchronously in the background.
3. Isolating individual recipient failures so a typo in one recipient's email does not abort the entire batch.
4. Providing real-time progress percentages and status updates.
5. Offering secure, database-backed certificate download endpoints.

---

## Key Features

- **Asynchronous Background Processing**: Offloads PDF generation from the HTTP request cycle using FastAPI's `BackgroundTasks`.
- **Fault-Tolerant Recipient Processing**: If one recipient fails (due to invalid email, empty name, or disk write glitch), only that recipient is marked `FAILED`. Remaining recipients continue seamlessly.
- **Accurate Job Status States**: Supports `QUEUED`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, and `FAILED`.
- **Predefined Professional Certificate Template**: High-resolution landscape A4 layout with navy & gold borders, official seal emblem, and clear typography built using ReportLab canvas.
- **Strict & Granular Validation**:
  - Rejects invalid job-level inputs (missing event details, empty recipient list, batch size exceeding limit) with **HTTP 422**.
  - Validates recipient-level data individually (whitespace names, bad email syntax, duplicate emails within a batch) without failing the whole request.
- **Prevent Path Traversal**: Certificate downloads resolve file paths strictly against the configured storage directory and database records.
- **Comprehensive Automated Tests**: 100% test coverage across job creation, progress tracking, validation rules, mock rendering failures, and certificate downloads.

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Modern type hints, high performance, robust ecosystem |
| **Web Framework** | FastAPI | Async support, high throughput, automatic OpenAPI documentation |
| **Server** | Uvicorn | Lightweight, production-grade ASGI web server |
| **Database** | SQLite | Serverless, zero-configuration relational database ideal for single-instance or embedded environments |
| **ORM** | SQLAlchemy 2.0+ | Robust declarative data mapping, relationship handling, and session management |
| **Validation** | Pydantic v2 | High-speed data parsing, input sanitation, and response schemas |
| **PDF Engine** | ReportLab | Mature, low-level canvas layout engine with vector graphics and precision typography |
| **Testing** | pytest & FastAPI TestClient | Fast, isolated unit and integration testing with in-memory database fixtures |

---

## System Architecture

```mermaid
flowchart TD
    Client([Client / Frontend]) -->|POST /api/v1/certificate-jobs| API[FastAPI Application]
    API -->|Validate Schema| Pydantic[Pydantic v2]
    Pydantic -->|Valid Payload| DB[(SQLite Database)]
    API -->|HTTP 202 Accepted + Job ID| Client
    API -.->|Enqueue BackgroundTask| Worker[Job Processor Worker]

    subgraph Background Execution
        Worker -->|Fetch PENDING Recipients| DB
        Worker -->|Iterate Each Recipient| Loop{Valid Recipient?}
        Loop -->|No: Empty / Bad Email / Duplicate| MarkFail[Mark Recipient FAILED]
        Loop -->|Yes| ReportLab[ReportLab PDF Engine]
        ReportLab -->|Render Landscape A4| Storage[(Local Storage: generated_certificates)]
        ReportLab -->|Success| MarkSuccess[Mark Recipient COMPLETED]
        ReportLab -->|Error| MarkFail
        MarkSuccess --> UpdateCounts[Update Job Counts & Progress]
        MarkFail --> UpdateCounts
        UpdateCounts --> ResolveStatus[Set Status: COMPLETED / COMPLETED_WITH_ERRORS / FAILED]
    end

    Client -->|GET /api/v1/certificate-jobs/{job_id}| API
    Client -->|GET /api/v1/certificates/{certificate_id}| API
    API -->|Stream PDF File| Client
```

---

## Prerequisites

- **Python**: Version 3.11 or later installed.
  - Verify by running `python --version` in your terminal.
- **Operating System**: Windows 10/11, macOS, or Linux.
- **Code Editor**: Visual Studio Code (recommended) or any modern IDE.

---

## Setup & Installation (Windows & VS Code)

### 1. Open the Project in VS Code
Open PowerShell or Windows Terminal and navigate to the project directory:
```powershell
cd C:\Users\swetha\.gemini\antigravity\scratch\bulk-certificate-generator
code .
```

### 2. Create and Activate a Virtual Environment
```powershell
# Create virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

### 3. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Configuration

The application reads configurations from environment variables or a `.env` file. A template `.env.example` is provided:

```powershell
# Copy the example environment file
Copy-Item .env.example .env
```

Default configuration in `.env`:
```env
APP_NAME="Bulk Certificate Generator"
APP_ENV="development"
DEBUG=True
API_V1_PREFIX="/api/v1"

# SQLite Database
DATABASE_URL="sqlite:///./certificates.db"

# Directory where generated PDF certificates are stored
CERTIFICATE_OUTPUT_DIR="./generated_certificates"

# Maximum recipients per single batch submission
MAX_BATCH_SIZE=500
```

---

## Running the Application

Start the local development server with Uvicorn:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The application will automatically:
- Initialize the SQLite database (`certificates.db`) and create required tables.
- Create the `./generated_certificates` directory if it does not exist.
- Start listening on `http://127.0.0.1:8000`.

---

## Interactive API Documentation

FastAPI provides built-in interactive OpenAPI documentation:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Running the Test Suite

Run the full automated test suite using pytest:

```powershell
pytest -v
```

### Test Coverage Highlights:
- `tests/test_jobs.py`: Health check, job creation, polling status, 404 nonexistent jobs, limit/offset pagination.
- `tests/test_certificates.py`: Direct ReportLab PDF generation, PDF magic bytes (`%PDF-`), download endpoint, 404 handling, and job certificates list.
- `tests/test_validation.py`: Missing fields, empty recipient list, whitespace fields, invalid dates, batch size > 500, recipient-level validation (whitespace names, invalid emails, duplicates).
- `tests/test_job_failures.py`: Simulated PDF generation exception isolation (ensures other recipients succeed), partial failure job status (`COMPLETED_WITH_ERRORS`), and 100% failure scenario (`FAILED`).

---

## API Reference & Examples

### 1. Health Check
Checks service operational status.

- **Endpoint**: `GET /health`
- **Response**: `200 OK`
```json
{
  "status": "healthy",
  "app": "Bulk Certificate Generator",
  "version": "1.0.0",
  "timestamp": "2026-10-12T05:22:18.929840Z"
}
```

---

### 2. Create Bulk Certificate Job
Submits a batch of recipients for certificate generation.

- **Endpoint**: `POST /api/v1/certificate-jobs`
- **Status Code**: `202 Accepted`

#### Example Request Body:
```json
{
  "event_name": "Python Programming Workshop",
  "certificate_title": "Certificate of Completion",
  "completion_date": "2026-10-10",
  "organization_name": "ABC Technologies",
  "recipients": [
    {
      "name": "Arun Kumar",
      "email": "arun@example.com",
      "extra_info": "High Distinction"
    },
    {
      "name": "Priya Sharma",
      "email": "priya@example.com"
    },
    {
      "name": "Karthik Raj",
      "email": "karthik@example.com"
    }
  ]
}
```

#### Example PowerShell Command:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/certificate-jobs" `
  -Method POST `
  -ContentType "application/json" `
  -Body (@{
    event_name = "Python Programming Workshop"
    certificate_title = "Certificate of Completion"
    completion_date = "2026-10-10"
    organization_name = "ABC Technologies"
    recipients = @(
      @{ name = "Arun Kumar"; email = "arun@example.com" },
      @{ name = "Priya Sharma"; email = "priya@example.com" }
    )
  } | ConvertTo-Json -Depth 5)
```

#### Example Response (`202 Accepted`):
```json
{
  "job_id": "afe6f018-03ba-41e7-9278-08ef96d06736",
  "status": "QUEUED",
  "total_recipients": 2,
  "status_url": "/api/v1/certificate-jobs/afe6f018-03ba-41e7-9278-08ef96d06736",
  "message": "Bulk certificate generation job accepted and queued for processing."
}
```

---

### 3. Check Job Status & Progress
Queries the current progress, counts, and individual recipient outcomes of a job.

- **Endpoint**: `GET /api/v1/certificate-jobs/{job_id}`
- **Status Code**: `200 OK`

#### Example PowerShell Command:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/certificate-jobs/afe6f018-03ba-41e7-9278-08ef96d06736"
```

#### Example Response (Partially Failed Job / `COMPLETED_WITH_ERRORS`):
```json
{
  "job_id": "afe6f018-03ba-41e7-9278-08ef96d06736",
  "event_name": "Full Stack Python Masterclass",
  "certificate_title": "Certificate of Excellence",
  "completion_date": "2026-10-12",
  "organization_name": "Antigravity Engineering",
  "status": "COMPLETED_WITH_ERRORS",
  "total_recipients": 4,
  "successful_count": 2,
  "failed_count": 2,
  "pending_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-12T05:22:18.940000Z",
  "started_at": "2026-10-12T05:22:18.980000Z",
  "completed_at": "2026-10-12T05:22:19.050000Z",
  "recipients": [
    {
      "id": 1,
      "name": "Arun Kumar",
      "email": "arun@example.com",
      "status": "COMPLETED",
      "certificate_id": "CERT-D169-42A0-FC5B",
      "download_url": "/api/v1/certificates/CERT-D169-42A0-FC5B",
      "error_message": null,
      "created_at": "2026-10-12T05:22:18.945000Z",
      "completed_at": "2026-10-12T05:22:19.016000Z"
    },
    {
      "id": 2,
      "name": "Priya Sharma",
      "email": "priya@example.com",
      "status": "COMPLETED",
      "certificate_id": "CERT-3602-DF54-EB0B",
      "download_url": "/api/v1/certificates/CERT-3602-DF54-EB0B",
      "error_message": null,
      "created_at": "2026-10-12T05:22:18.946000Z",
      "completed_at": "2026-10-12T05:22:19.040000Z"
    },
    {
      "id": 3,
      "name": "   ",
      "email": "whitespace_name@example.com",
      "status": "FAILED",
      "certificate_id": null,
      "download_url": null,
      "error_message": "Recipient name cannot be empty or contain only whitespace.",
      "created_at": "2026-10-12T05:22:18.947000Z",
      "completed_at": "2026-10-12T05:22:19.042000Z"
    },
    {
      "id": 4,
      "name": "Duplicate User",
      "email": "arun@example.com",
      "status": "FAILED",
      "certificate_id": null,
      "download_url": null,
      "error_message": "Duplicate recipient email within the same job batch: 'arun@example.com'",
      "created_at": "2026-10-12T05:22:18.948000Z",
      "completed_at": "2026-10-12T05:22:19.045000Z"
    }
  ]
}
```

---

### 4. List Jobs (Paginated)
Retrieves historical generation jobs.

- **Endpoint**: `GET /api/v1/certificate-jobs?limit=10&offset=0`
- **Query Parameters**:
  - `limit` (default: 10, min: 1, max: 100)
  - `offset` (default: 0, min: 0)

#### Example Response:
```json
{
  "items": [
    {
      "id": "afe6f018-03ba-41e7-9278-08ef96d06736",
      "event_name": "Full Stack Python Masterclass",
      "certificate_title": "Certificate of Excellence",
      "organization_name": "Antigravity Engineering",
      "status": "COMPLETED_WITH_ERRORS",
      "total_recipients": 4,
      "successful_count": 2,
      "failed_count": 2,
      "pending_count": 0,
      "progress_percentage": 100.0,
      "created_at": "2026-10-12T05:22:18.940000Z",
      "started_at": "2026-10-12T05:22:18.980000Z",
      "completed_at": "2026-10-12T05:22:19.050000Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

---

### 5. Download Certificate PDF
Streams the generated PDF file for a verified certificate.

- **Endpoint**: `GET /api/v1/certificates/{certificate_id}`
- **Response**: `200 OK` (binary `application/pdf`) or `404 Not Found`

#### Example PowerShell Download:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/certificates/CERT-D169-42A0-FC5B" `
  -OutFile "my_certificate.pdf"
```

---

### 6. List Certificates for Job
Lists all successful certificates generated under a given job.

- **Endpoint**: `GET /api/v1/certificate-jobs/{job_id}/certificates`
- **Response**: `200 OK`
```json
[
  {
    "certificate_id": "CERT-D169-42A0-FC5B",
    "recipient_name": "Arun Kumar",
    "recipient_email": "arun@example.com",
    "event_name": "Full Stack Python Masterclass",
    "organization_name": "Antigravity Engineering",
    "completion_date": "2026-10-12",
    "download_url": "/api/v1/certificates/CERT-D169-42A0-FC5B",
    "issued_at": "2026-10-12T05:22:19.016000Z"
  }
]
```

---

## Database Schema

```
+---------------------------------------------------------------------------------+
|                               certificate_jobs                                  |
+---------------------------------------------------------------------------------+
| id                 | VARCHAR(36)  | PRIMARY KEY (UUID)                          |
| event_name         | VARCHAR(255) | NOT NULL                                    |
| certificate_title  | VARCHAR(255) | NOT NULL, DEFAULT 'Certificate of Completion|
| completion_date    | VARCHAR(50)  | NOT NULL                                    |
| organization_name  | VARCHAR(255) | NOT NULL                                    |
| status             | VARCHAR(50)  | NOT NULL, INDEX (QUEUED, PROCESSING, etc.)  |
| total_recipients   | INTEGER      | NOT NULL, DEFAULT 0                         |
| successful_count   | INTEGER      | NOT NULL, DEFAULT 0                         |
| failed_count       | INTEGER      | NOT NULL, DEFAULT 0                         |
| created_at         | DATETIME     | NOT NULL, INDEX                             |
| started_at         | DATETIME     | NULLABLE                                    |
| completed_at       | DATETIME     | NULLABLE                                    |
+---------------------------------------------------------------------------------+
                                      |
                                  1 to Many
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                             certificate_recipients                              |
+---------------------------------------------------------------------------------+
| id                 | INTEGER      | PRIMARY KEY, AUTOINCREMENT                  |
| job_id             | VARCHAR(36)  | FOREIGN KEY -> certificate_jobs.id, INDEX   |
| name               | VARCHAR(255) | NOT NULL                                    |
| email              | VARCHAR(255) | NOT NULL, INDEX                             |
| status             | VARCHAR(50)  | NOT NULL, INDEX (PENDING, PROCESSING, etc.) |
| certificate_id     | VARCHAR(64)  | UNIQUE, INDEX, NULLABLE                     |
| certificate_path   | VARCHAR(500) | NULLABLE                                    |
| error_message      | TEXT         | NULLABLE                                    |
| created_at         | DATETIME     | NOT NULL                                    |
| completed_at       | DATETIME     | NULLABLE                                    |
+---------------------------------------------------------------------------------+
```

---

## Certificate Storage & Security

- **File Naming**: Each certificate is named `{certificate_id}.pdf` using a cryptographically randomized, collision-resistant identifier (e.g., `CERT-D169-42A0-FC5B`).
- **Path Traversal Protection**: Clients cannot specify filesystem paths. The download endpoint queries the database for the recipient's record and verifies that the resolved path is located strictly within `CERTIFICATE_OUTPUT_DIR`.
- **State Verification**: Downloading is disallowed if the recipient's status is not `COMPLETED`.

---

## Design Decisions

1. **In-Process BackgroundTasks vs. Message Queue (Celery/RabbitMQ)**:
   - For an assignment and small-to-medium batches (up to 500 recipients), FastAPI's built-in `BackgroundTasks` avoids external infrastructure complexity (Redis, RabbitMQ, Celery workers), making setup seamless on any machine.
2. **Granular Recipient Validation Policy**:
   - In bulk operations, discarding an entire batch of 499 valid recipients because recipient #500 had an invalid email creates a terrible user experience.
   - We enforce strict HTTP 422 errors for job-level syntax and payload errors, but isolate recipient-level flaws to individual recipient records.
3. **Session Thread Safety**:
   - In background tasks, using the request's database session across threads causes concurrency bugs. The background worker instantiates its own dedicated `SessionLocal()` and guarantees session disposal in a `finally` block.
4. **Calculated Properties**:
   - Progress percentage and pending counts are derived with defensive division-by-zero checks (`total_recipients <= 0 -> 0.0%`).

---

## Background Processing & Limitations

### Documented Limitations:
- **Server Restart Job Loss**: Because tasks reside in the Python process memory, shutting down or restarting the Uvicorn server while a job is `QUEUED` or `PROCESSING` will interrupt that job.
- **Single-Node Scaling**: In-process background processing is tied to the memory and CPU of the host server.
- **Worker Concurrency**: If thousands of large bulk jobs arrive simultaneously, processing them in-process can saturate server CPU and memory.

---

## Future Improvements

1. **Distributed Task Queue**: Introduce Celery or ARQ backed by Redis for durable, multi-worker task execution surviving server restarts.
2. **Object Storage**: Store certificates in Amazon S3, Google Cloud Storage, or MinIO instead of local disk storage.
3. **Email Notification Service**: Send certificates directly to recipients' email addresses via SMTP or SendGrid upon generation.
4. **Custom Templates / Branding**: Support uploading organization logos and selecting from multiple certificate styling themes.
