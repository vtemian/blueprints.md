import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/ecommerce"
)

# Create engine with connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create base class for declarative models
Base = declarative_base()
metadata = MetaData()

def get_db() -> Session:
    """
    Get database session from connection pool.
    
    Returns:
        Session: Database session
    """
    db = SessionLocal()
    try:
        return db
    except SQLAlchemyError as e:
        db.rollback()
        raise SQLAlchemyError(f"Database error: {str(e)}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan_db_context() -> AsyncGenerator[None, None]:
    """
    Lifecycle context manager for database connections.
    Creates tables on startup and cleans up on shutdown.
    """
    try:
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        engine.dispose()

def init_db() -> None:
    """Initialize database by creating all tables."""
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        raise SQLAlchemyError(f"Failed to initialize database: {str(e)}")

def get_session() -> Session:
    """
    Get new database session.
    
    Returns:
        Session: New database session
    """
    return SessionLocal()

def close_session(session: Session) -> None:
    """
    Close database session.
    
    Args:
        session: Database session to close
    """
    if session:
        session.close()