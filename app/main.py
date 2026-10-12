"""FastAPI main application entry point.

Configures lifespan startup/shutdown, routers, exception handling, and health check.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.database import init_db
from app.routers import certificates, jobs
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager that initializes database tables and storage on startup."""
    # Startup: ensure tables exist without destroying existing data
    init_db()
    yield
    # Shutdown logic (if any cleanup is required)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-minded REST API for bulk certificate generation with background "
        "processing, failure isolation, ReportLab PDF rendering, and progress tracking."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend clients / testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routers
app.include_router(jobs.router, prefix=settings.API_V1_PREFIX)
app.include_router(certificates.router, prefix=settings.API_V1_PREFIX)


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health check endpoint",
    description="Returns the operational status, application name, version, and server timestamp.",
)
def health_check() -> HealthResponse:
    """Check application health status."""
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger API documentation."""
    return RedirectResponse(url="/docs")
