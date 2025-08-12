"""
Main FastAPI application module.

This module contains the FastAPI application factory with middleware,
routing, exception handling, and lifecycle management.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api import tasks, users
from core import database
from core.database import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Custom Exception Classes
class APIError(Exception):
    """Base API exception class."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseError(APIError):
    """Database-related exception."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=503)


class NotFoundError(APIError):
    """Resource not found exception."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


# Application Lifespan Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application,
    including database connection initialization and cleanup.
    """
    # Startup
    logger.info("Starting up application...")
    try:
        # Initialize database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Run any additional startup tasks here
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        # Close database connections
        engine.dispose()
        logger.info("Database connections closed")
        
        # Run any additional cleanup tasks here
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


def create_app() -> FastAPI:
    """
    FastAPI application factory.
    
    Creates and configures the FastAPI application with middleware,
    routing, exception handlers, and other settings.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    # Create FastAPI instance with configuration
    app = FastAPI(
        title="Task Management API",
        description="A comprehensive task management system with user authentication",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Configure CORS Middleware (must be added first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React development server
            "http://localhost:8080",  # Vue development server
            "https://yourdomain.com",  # Production frontend
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Custom Request/Response Logging Middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next) -> Response:
        """
        Log HTTP requests and responses with timing information.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            Response: The HTTP response
        """
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state for use in handlers
        request.state.request_id = request_id
        
        # Log request details
        start_time = time.time()
        logger.info(
            f"Request started - ID: {request_id} | "
            f"Method: {request.method} | "
            f"URL: {request.url} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response details
            logger.info(
                f"Request completed - ID: {request_id} | "
                f"Status: {response.status_code} | "
                f"Time: {process_time:.4f}s"
            )
            
            return response
            
        except Exception as e:
            # Calculate processing time for failed requests
            process_time = time.time() - start_time
            
            # Log error details
            logger.error(
                f"Request failed - ID: {request_id} | "
                f"Error: {str(e)} | "
                f"Time: {process_time:.4f}s"
            )
            
            # Re-raise the exception to be handled by exception handlers
            raise
    
    # Global Exception Handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with structured error response."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": request_id,
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors with detailed field information."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "request_id": request_id,
                }
            }
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Data validation failed",
                    "details": exc.errors(),
                    "request_id": request_id,
                }
            }
        )
    
    @app.exception_handler(APIError)
    async def api_exception_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle custom API exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "status_code": exc.status_code,
                    "request_id": request_id,
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions with generic error response."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log the full exception for debugging
        logger.exception(f"Unhandled exception for request {request_id}: {exc}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                }
            }
        )
    
    # Health Check Endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint that verifies application and database status.
        
        Returns:
            Dict containing health status information
        """
        try:
            # Check database connectivity
            db_status = await database.health_check()
            
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "services": {
                    "api": "healthy",
                    "database": "healthy" if db_status else "unhealthy"
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "timestamp": time.time(),
                    "services": {
                        "api": "healthy",
                        "database": "unhealthy"
                    },
                    "error": str(e)
                }
            )
    
    # Include API Routers
    app.include_router(
        users.router,
        prefix="/api/v1/users",
        tags=["Users"]
    )
    
    app.include_router(
        tasks.router,
        prefix="/api/v1/tasks",
        tags=["Tasks"]
    )
    
    return app


# Create the application instance
app = create_app()


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint providing basic API information.
    
    Returns:
        Dict containing welcome message and API information
    """
    return {
        "message": "Welcome to Task Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the application with uvicorn for development
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
