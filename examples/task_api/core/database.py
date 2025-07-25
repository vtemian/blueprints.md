import os
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from models.user import User
from models.task import Task

# Database URL configuration
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

# Engine configuration with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# Session configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()

# Enable foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def init_db() -> None:
    """Initialize database tables and create initial schema"""
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        raise RuntimeError(f"Failed to initialize database: {str(e)}")

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency that handles session lifecycle
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Database error occurred: {str(e)}")
    finally:
        db.close()

def check_db_health() -> bool:
    """
    Check database connection health
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return True
    except Exception:
        return False