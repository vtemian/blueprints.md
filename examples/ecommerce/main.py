import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown events"""
    try:
        # Startup
        logger.info("Starting up application...")
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        # Shutdown
        logger.info("Shutting down application...")

# Create FastAPI app instance
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health check - verify DB connection
        db = SessionLocal()
        db.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)