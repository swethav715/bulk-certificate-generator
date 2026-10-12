"""Database configuration and session management.

Sets up SQLAlchemy engine, session factory, declarative base, and FastAPI
dependency for database session injection.
"""

from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# SQLite requires check_same_thread=False when accessed across threads (such as BackgroundTasks)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and create certificate output directory if missing."""
    Base.metadata.create_all(bind=engine)
    
    # Ensure certificate storage directory exists
    output_path = Path(settings.CERTIFICATE_OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
