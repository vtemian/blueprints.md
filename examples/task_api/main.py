"""
FastAPI Task Management API - Main Application Module

This module serves as the entry point for the FastAPI task management application.
It handles app initialization, middleware configuration, database setup, and
development server configuration.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log") if os.getenv("LOG_TO_FILE", "false").lower() == "true" else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import application modules with error handling
try:
    from core.database import engine, Base, get_database_url
    from api.users import router as users_router
    from api.tasks import router as tasks_router
    from models.user import User  # Import to ensure table creation
    from models.task import Task  # Import to ensure table creation
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup events
    logger.info("Starting up FastAPI application...")
    
    try:
        # Create database tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Log application configuration
        logger.info(f"Database URL: {get_database_url(mask_password=True)}")
        logger.info(f"Debug mode: {os.getenv('DEBUG', 'false')}")
        logger.info(f"CORS origins: {os.getenv('CORS_ORIGINS', '*')}")
        
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {e}")
        raise RuntimeError("Failed to initialize database") from e
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise RuntimeError("Failed to start application") from e
    
    yield
    
    # Shutdown events
    logger.info("Shutting down FastAPI application...")
    try:
        # Dispose of database connections
        engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Initialize FastAPI application
app = FastAPI(
    title="Task Management API",
    description="A comprehensive task management system with user authentication and task CRUD operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log HTTP requests and responses.
    
    Args:
        request: HTTP request object
        call_next: Next middleware/endpoint in the chain
        
    Returns:
        HTTP response object
    """
    start_time = request.state.start_time = __import__('time').time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path} - Client: {request.client.host}")
    
    try:
        response = await call_next(request)
        
        # Log response
        process_time = __import__('time').time() - start_time
        logger.info(
            f"Response: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"Path: {request.url.path}"
        )
        
        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = __import__('time').time() - start_time
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.4f}s")
        raise


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with proper logging and response formatting.
    
    Args:
        request: HTTP request object
        exc: HTTP exception
        
    Returns:
        JSON response with error details
    """
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors with detailed error information.
    
    Args:
        request: HTTP request object
        exc: Validation exception
        
    Returns:
        JSON response with validation error details
    """
    logger.warning(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database-related exceptions.
    
    Args:
        request: HTTP request object
        exc: SQLAlchemy exception
        
    Returns:
        JSON response with database error information
    """
    logger.error(f"Database error: {str(exc)} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Database operation failed",
            "status_code": 500,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with proper logging.
    
    Args:
        request: HTTP request object
        exc: General exception
        
    Returns:
        JSON response with generic error message
    """
    logger.error(f"Unexpected error: {str(exc)} - Path: {request.url.path}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
            "path": str(request.url.path)
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify API status and database connectivity.
    
    Returns:
        Dict containing health status information
    """
    try:
        # Test database connection
        with engine.connect() as connection:
            connection.execute(__import__('sqlalchemy').text("SELECT 1"))
        
        return {
            "status": "healthy",
            "message": "API is running successfully",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint providing basic API information.
    
    Returns:
        Dict with welcome message and API information
    """
    return {
        "message": "Welcome to Task Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include API routers
app.include_router(
    users_router,
    prefix="/api/v1/users",
    tags=["Users"]
)

app.include_router(
    tasks_router,
    prefix="/api/v1/tasks",
    tags=["Tasks"]
)

logger.info("FastAPI application configured successfully")


# Development server configuration
if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting development server on {host}:{port}")
    logger.info(f"Debug mode: {debug}, Hot reload: {reload}")
    
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info" if debug else "warning",
            access_log=debug,
            reload_dirs=["./"] if reload else None,
            reload_excludes=["*.log", "*.pyc", "__pycache__", ".git"] if reload else None
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)