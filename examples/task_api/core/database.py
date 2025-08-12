"""
Database connection and session management module.

This module provides database connectivity, session management, health checks,
and Alembic integration for FastAPI applications.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional, Tuple, Any, Dict

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration constants
DEFAULT_DATABASE_URL = "sqlite:///./app.db"
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 3600  # 1 hour
HEALTH_CHECK_TIMEOUT = 5

# Create declarative base for models
Base = declarative_base()


class DatabaseError(Exception):
    """Custom database exception."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Database connection specific exception."""
    pass


class DatabaseConfig:
    """Database configuration class."""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.pool_size = int(os.getenv("DB_POOL_SIZE", DEFAULT_POOL_SIZE))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", DEFAULT_MAX_OVERFLOW))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", DEFAULT_POOL_TIMEOUT))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", DEFAULT_POOL_RECYCLE))
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"
        
    def _get_database_url(self) -> str:
        """Get database URL from environment with validation."""
        database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
            
        # Handle Heroku postgres URL format
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
            
        return database_url
    
    def get_engine_kwargs(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration."""
        kwargs = {
            "echo": self.echo,
            "future": True,  # Use SQLAlchemy 2.0 style
        }
        
        # Only add pooling config for non-SQLite databases
        if not self.database_url.startswith("sqlite"):
            kwargs.update({
                "poolclass": QueuePool,
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": True,  # Validate connections before use
            })
        else:
            # SQLite specific configuration
            kwargs.update({
                "connect_args": {"check_same_thread": False},
                "poolclass": pool.StaticPool,
            })
            
        return kwargs


# Global configuration instance
config = DatabaseConfig()

# Create database engine
engine: Engine = create_engine(config.database_url, **config.get_engine_kwargs())

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance and reliability."""
    if config.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=memory")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
        cursor.close()


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout events."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin events."""
    logger.debug("Connection returned to pool")


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self._session_factory = SessionLocal
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic cleanup.
        
        Yields:
            Session: SQLAlchemy database session
            
        Raises:
            DatabaseError: If session creation or operation fails
        """
        session = self._session_factory()
        try:
            logger.debug("Database session created")
            yield session
            session.commit()
            logger.debug("Database session committed")
        except SQLAlchemyError as e:
            logger.error(f"Database error occurred: {str(e)}")
            session.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error in database session: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
            logger.debug("Database session closed")
    
    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise DatabaseError(f"Table creation failed: {str(e)}") from e
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise DatabaseError(f"Table dropping failed: {str(e)}") from e
    
    def dispose(self) -> None:
        """Dispose of the database engine and close all connections."""
        try:
            self.engine.dispose()
            logger.info("Database engine disposed successfully")
        except Exception as e:
            logger.error(f"Error disposing database engine: {str(e)}")


# Global database manager instance
db_manager = DatabaseManager(engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency function for database sessions.
    
    This function provides database sessions to FastAPI route handlers
    with automatic cleanup and error handling.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/users/")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    session = SessionLocal()
    try:
        logger.debug("FastAPI database session created")
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error in FastAPI dependency: {str(e)}")
        session.rollback()
        raise DatabaseError(f"Database operation failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error in FastAPI database dependency: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug("FastAPI database session closed")


def check_database_health() -> Tuple[bool, Optional[str]]:
    """
    Check database connectivity and health.
    
    Returns:
        Tuple[bool, Optional[str]]: (is_healthy, error_message)
        
    Example:
        is_healthy, error = check_database_health()
        if not is_healthy:
            logger.error(f"Database health check failed: {error}")
    """
    try:
        with engine.connect() as connection:
            # Set a timeout for the health check query
            connection = connection.execution_options(
                autocommit=True,
                compiled_cache={}
            )
            
            # Execute a simple query to test connectivity
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            
        logger.debug("Database health check passed")
        return True, None
        
    except DisconnectionError as e:
        error_msg = "Database connection lost"
        logger.error(f"Database health check failed: {error_msg} - {str(e)}")
        return False, error_msg
        
    except SQLAlchemyError as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(f"Database health check failed: {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error during health check: {str(e)}"
        logger.error(f"Database health check failed: {error_msg}")
        return False, error_msg


class AlembicManager:
    """Manager for Alembic database migrations."""
    
    def __init__(self, alembic_cfg_path: str = "alembic.ini"):
        self.alembic_cfg_path = alembic_cfg_path
        self._config: Optional[Config] = None
    
    @property
    def config(self) -> Config:
        """Get Alembic configuration with database URL."""
        if self._config is None:
            if not os.path.exists(self.alembic_cfg_path):
                raise FileNotFoundError(f"Alembic config file not found: {self.alembic_cfg_path}")
                
            self._config = Config(self.alembic_cfg_path)
            # Set database URL programmatically
            self._config.set_main_option("sqlalchemy.url", config.database_url)
            
        return self._config
    
    def upgrade(self, revision: str = "head") -> None:
        """
        Run database migrations up to specified revision.
        
        Args:
            revision: Target revision (default: "head" for latest)
        """
        try:
            logger.info(f"Running database upgrade to revision: {revision}")
            command.upgrade(self.config, revision)
            logger.info("Database upgrade completed successfully")
        except Exception as e:
            logger.error(f"Database upgrade failed: {str(e)}")
            raise DatabaseError(f"Migration upgrade failed: {str(e)}") from e
    
    def downgrade(self, revision: str) -> None:
        """
        Run database migrations down to specified revision.
        
        Args:
            revision: Target revision to downgrade to
        """
        try:
            logger.info(f"Running database downgrade to revision: {revision}")
            command.downgrade(self.config, revision)
            logger.info("Database downgrade completed successfully")
        except Exception as e:
            logger.error(f"Database downgrade failed: {str(e)}")
            raise DatabaseError(f"Migration downgrade failed: {str(e)}") from e
    
    def current(self) -> None:
        """Show current database revision."""
        try:
            command.current(self.config)
        except Exception as e:
            logger.error(f"Failed to get current revision: {str(e)}")
            raise DatabaseError(f"Failed to get current revision: {str(e)}") from e
    
    def history(self) -> None:
        """Show migration history."""
        try:
            command.history(self.config)
        except Exception as e:
            logger.error(f"Failed to get migration history: {str(e)}")
            raise DatabaseError(f"Failed to get migration history: {str(e)}") from e
    
    def create_revision(self, message: str, autogenerate: bool = True) -> None:
        """
        Create a new migration revision.
        
        Args:
            message: Migration message/description
            autogenerate: Whether to auto-generate migration from model changes
        """
        try:
            logger.info(f"Creating new migration: {message}")
            command.revision(
                self.config,
                message=message,
                autogenerate=autogenerate
            )
            logger.info("Migration created successfully")
        except Exception as e:
            logger.error(f"Failed to create migration: {str(e)}")
            raise DatabaseError(f"Migration creation failed: {str(e)}") from e


# Global Alembic manager instance
alembic_manager = AlembicManager()


def init_database() -> None:
    """Initialize database with tables and run migrations."""
    try:
        logger.info("Initializing database...")
        
        # Check database health first
        is_healthy, error = check_database_health()
        if not is_healthy:
            raise DatabaseConnectionError(f"Database is not healthy: {error}")
        
        # Run migrations
        alembic_manager.upgrade()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise DatabaseError(f"Database initialization failed: {str(e)}") from e


def close_database() -> None:
    """Close database connections and cleanup resources."""
    try:
        logger.info("Closing database connections...")
        db_manager.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")


# Utility functions for common database operations
def execute_raw_sql(sql: str, params: Optional[Dict] = None) -> Any:
    """
    Execute raw SQL query with proper session management.
    
    Args:
        sql: SQL query string
        params: Query parameters
        
    Returns:
        Query result
    """
    with db_manager.get_session() as session:
        try:
            result = session.execute(text(sql), params or {})
            return result.fetchall()
        except SQLAlchemyError as e:
            logger.error(f"Raw SQL execution failed: {str(e)}")
            raise DatabaseError(f"SQL execution failed: {str(e)}") from e


def get_database_info() -> Dict[str, Any]:
    """
    Get database information and statistics.
    
    Returns:
        Dict containing database information
    """
    try:
        with engine.connect() as connection:
            # Get basic database info
            info = {
                "url": config.database_url.split("@")[-1] if "@" in config.database_url else config.database_url,
                "pool_size": config.pool_size,
                "max_overflow": config.max_overflow,
                "pool_timeout": config.pool_timeout,
                "echo": config.echo,
            }
            
            # Add pool statistics if available
            if hasattr(engine.pool, 'size'):
                info.update({
                    "pool_current_size": engine.pool.size(),
                    "pool_checked_in": engine.pool.checkedin(),
                    "pool_checked_out": engine.pool.checkedout(),
                })
            
            return info
            
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        return {"error": str(e)}