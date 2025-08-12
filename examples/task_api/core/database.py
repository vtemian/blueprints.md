"""
Database connection and session management module.

This module provides database connectivity, session management, and utilities
for FastAPI applications using SQLAlchemy with async support.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration constants
DEFAULT_DATABASE_URL = "sqlite:///./app.db"
DEFAULT_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./app.db"
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 3600
DEFAULT_CONNECTION_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2

# Create declarative base for models
Base = declarative_base()


class DatabaseConfig:
    """Database configuration class."""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.async_database_url = self._get_async_database_url()
        self.pool_size = int(os.getenv("DB_POOL_SIZE", DEFAULT_POOL_SIZE))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", DEFAULT_POOL_TIMEOUT))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", DEFAULT_POOL_RECYCLE))
        self.connection_timeout = int(os.getenv("DB_CONNECTION_TIMEOUT", DEFAULT_CONNECTION_TIMEOUT))
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"
        
    def _get_database_url(self) -> str:
        """Get database URL from environment with validation."""
        url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        if not self._validate_database_url(url):
            logger.warning(f"Invalid DATABASE_URL format, using default: {DEFAULT_DATABASE_URL}")
            return DEFAULT_DATABASE_URL
        return url
    
    def _get_async_database_url(self) -> str:
        """Get async database URL from environment or convert sync URL."""
        async_url = os.getenv("ASYNC_DATABASE_URL")
        if async_url:
            return async_url
            
        # Convert sync URL to async URL
        sync_url = self.database_url
        if sync_url.startswith("postgresql://"):
            return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif sync_url.startswith("mysql://"):
            return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
        elif sync_url.startswith("sqlite:///"):
            return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        else:
            return DEFAULT_ASYNC_DATABASE_URL
    
    def _validate_database_url(self, url: str) -> bool:
        """Validate database URL format."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and (parsed.path or parsed.netloc))
        except Exception as e:
            logger.error(f"Error validating database URL: {e}")
            return False


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[sessionmaker] = None
        
    @property
    def engine(self) -> Engine:
        """Get or create synchronous database engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def async_engine(self) -> AsyncEngine:
        """Get or create asynchronous database engine."""
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._session_factory
    
    @property
    def async_session_factory(self) -> sessionmaker:
        """Get or create async session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._async_session_factory
    
    def _create_engine(self) -> Engine:
        """Create synchronous database engine with connection pooling."""
        engine_kwargs = {
            "echo": self.config.echo,
            "pool_pre_ping": True,
            "pool_recycle": self.config.pool_recycle,
            "connect_args": {"timeout": self.config.connection_timeout}
        }
        
        # Configure pooling based on database type
        if self.config.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": self.config.connection_timeout
                }
            })
        else:
            engine_kwargs.update({
                "poolclass": QueuePool,
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
            })
        
        logger.info("Creating database engine")
        return create_engine(self.config.database_url, **engine_kwargs)
    
    def _create_async_engine(self) -> AsyncEngine:
        """Create asynchronous database engine with connection pooling."""
        engine_kwargs = {
            "echo": self.config.echo,
            "pool_pre_ping": True,
            "pool_recycle": self.config.pool_recycle,
        }
        
        # Configure pooling based on database type
        if self.config.async_database_url.startswith("sqlite"):
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False}
            })
        else:
            engine_kwargs.update({
                "poolclass": QueuePool,
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
            })
        
        logger.info("Creating async database engine")
        return create_async_engine(self.config.async_database_url, **engine_kwargs)
    
    async def create_tables(self):
        """Create all database tables."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all database tables."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    
    def get_session(self) -> Session:
        """Get a new synchronous database session."""
        return self.session_factory()
    
    def get_async_session(self) -> AsyncSession:
        """Get a new asynchronous database session."""
        return self.async_session_factory()
    
    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.get_async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """
        Perform database health check with retry logic.
        
        Returns:
            bool: True if database is healthy, False otherwise.
        """
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                async with self.async_engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Database health check passed")
                return True
            except Exception as e:
                wait_time = RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(
                    f"Database health check failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}"
                )
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Database health check failed after all retry attempts")
        
        return False
    
    async def close(self):
        """Close database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Async database engine disposed")
        
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine disposed")


# Global database manager instance
db_manager = DatabaseManager()


# FastAPI dependency functions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting database session.
    
    Yields:
        AsyncSession: Database session with automatic cleanup.
    """
    async with db_manager.session_scope() as session:
        yield session


async def get_db_session() -> AsyncSession:
    """
    Alternative FastAPI dependency for getting database session.
    Note: Requires manual session management.
    
    Returns:
        AsyncSession: Database session.
    """
    return db_manager.get_async_session()


# Utility functions
async def init_database():
    """Initialize database and create tables."""
    try:
        await db_manager.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database():
    """Close database connections."""
    await db_manager.close()


# Alembic configuration helpers
def get_alembic_config(ini_path: str = "alembic.ini") -> Config:
    """
    Get Alembic configuration.
    
    Args:
        ini_path: Path to alembic.ini file.
        
    Returns:
        Config: Alembic configuration object.
    """
    config = Config(ini_path)
    config.set_main_option("sqlalchemy.url", db_manager.config.database_url)
    return config


def run_migrations(revision: str = "head", ini_path: str = "alembic.ini"):
    """
    Run database migrations.
    
    Args:
        revision: Target revision (default: "head").
        ini_path: Path to alembic.ini file.
    """
    try:
        config = get_alembic_config(ini_path)
        command.upgrade(config, revision)
        logger.info(f"Migrations completed successfully to revision: {revision}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def create_migration(message: str, ini_path: str = "alembic.ini"):
    """
    Create a new migration.
    
    Args:
        message: Migration message.
        ini_path: Path to alembic.ini file.
    """
    try:
        config = get_alembic_config(ini_path)
        command.revision(config, message=message, autogenerate=True)
        logger.info(f"Migration created: {message}")
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise


# Context manager for database operations
@asynccontextmanager
async def database_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions with automatic rollback on error.
    
    Yields:
        AsyncSession: Database session within transaction context.
    """
    async with db_manager.session_scope() as session:
        yield session


# Health check endpoint helper
async def database_health_status() -> dict:
    """
    Get detailed database health status.
    
    Returns:
        dict: Health status information.
    """
    start_time = time.time()
    is_healthy = await db_manager.health_check()
    response_time = time.time() - start_time
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "response_time_ms": round(response_time * 1000, 2),
        "database_url": db_manager.config.database_url.split("@")[-1] if "@" in db_manager.config.database_url else "local",
        "pool_size": db_manager.config.pool_size,
        "max_overflow": db_manager.config.max_overflow
    }


# Export commonly used items
__all__ = [
    "Base",
    "DatabaseConfig",
    "DatabaseManager",
    "db_manager",
    "get_db",
    "get_db_session",
    "init_database",
    "close_database",
    "database_transaction",
    "database_health_status",
    "run_migrations",
    "create_migration",
    "get_alembic_config"
]