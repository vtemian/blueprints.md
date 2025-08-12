import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "taskdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass


class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    async def init_db(self) -> None:
        """Initialize database connection and session maker"""
        try:
            self.engine = create_async_engine(
                DATABASE_URL,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close_db(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup"""
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized")
            
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def check_health(self) -> bool:
        """Check database connectivity"""
        if not self.async_session_maker:
            return False
            
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def run_migrations(self, script_location: str = "alembic") -> None:
        """Run database migrations using Alembic"""
        try:
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", script_location)
            alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))
            command.upgrade(alembic_cfg, "head")
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise


# Global database instance
db = DatabaseManager()