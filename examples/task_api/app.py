"""
FastAPI Application Module

Main FastAPI application with middleware, routing, and comprehensive error handling.
Provides a production-ready setup with CORS, logging, health checks, and API routing.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import API routers
try:
    from api.users import router as users_router
except ImportError as e:
    logging.error(f"Failed to import users router: {e}")
    users_router = None

try:
    from api.tasks import router as tasks_router
except ImportError as e:
    logging.error(f"Failed to import tasks router: {e}")
    tasks_router = None

# Import database utilities
try:
    from core.database import init_database, close_database, get_database_status
except ImportError as e:
    logging.error(f"Failed to import database utilities: {e}")
    init_database = close_database = get_database_status = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Response Models
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    request_id: str
    timestamp: str
    status_code: int

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    database: str
    uptime_seconds: float

class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    error: str
    message: str
    details: list[Dict[str, Any]]
    request_id: str
    timestamp: str
    status_code: int

# Application startup time for uptime calculation
app_start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles database initialization and cleanup, along with other
    resource management tasks.
    """
    # Startup
    logger.info("Starting FastAPI application...")
    
    try:
        # Initialize database connection
        if init_database:
            await init_database()
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization function not available")
            
        # Add any other startup tasks here
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    
    try:
        # Close database connections
        if close_database:
            await close_database()
            logger.info("Database connections closed")
            
        # Add any other cleanup tasks here
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    
    # Initialize FastAPI application
    app = FastAPI(
        title="Task Management API",
        description="A comprehensive task management system with user authentication and task operations",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React development server
            "http://localhost:8080",  # Vue development server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            # Add production origins here
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add custom logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """
        Custom middleware for request/response logging and timing.
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started - ID: {request_id} | "
            f"Method: {request.method} | "
            f"URL: {request.url} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed - ID: {request_id} | "
                f"Status: {response.status_code} | "
                f"Duration: {process_time:.4f}s"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed - ID: {request_id} | "
                f"Error: {str(e)} | "
                f"Duration: {process_time:.4f}s"
            )
            raise
    
    # Include API routers
    if users_router:
        app.include_router(
            users_router,
            prefix="/api/v1/users",
            tags=["users"],
            responses={
                404: {"description": "User not found"},
                422: {"description": "Validation error"}
            }
        )
        logger.info("Users router included successfully")
    else:
        logger.warning("Users router not available - skipping inclusion")
    
    if tasks_router:
        app.include_router(
            tasks_router,
            prefix="/api/v1/tasks",
            tags=["tasks"],
            responses={
                404: {"description": "Task not found"},
                422: {"description": "Validation error"}
            }
        )
        logger.info("Tasks router included successfully")
    else:
        logger.warning("Tasks router not available - skipping inclusion")
    
    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent error format."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        logger.warning(
            f"HTTP Exception - ID: {request_id} | "
            f"Status: {exc.status_code} | "
            f"Detail: {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP_ERROR",
                message=str(exc.detail),
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                status_code=exc.status_code
            ).dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors with detailed information."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        logger.warning(
            f"Validation Error - ID: {request_id} | "
            f"Errors: {exc.errors()}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ValidationErrorResponse(
                error="VALIDATION_ERROR",
                message="Request validation failed",
                details=exc.errors(),
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            ).dict()
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        logger.warning(
            f"Pydantic Validation Error - ID: {request_id} | "
            f"Errors: {exc.errors()}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ValidationErrorResponse(
                error="VALIDATION_ERROR",
                message="Data validation failed",
                details=exc.errors(),
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        logger.error(
            f"Unexpected Error - ID: {request_id} | "
            f"Type: {type(exc).__name__} | "
            f"Message: {str(exc)}",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred",
                request_id=request_id,
                timestamp=datetime.utcnow().isoformat(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            ).dict()
        )
    
    # Health check endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Health Check",
        description="Check the health status of the application and its dependencies"
    )
    async def health_check():
        """
        Health check endpoint that returns application status and basic system information.
        
        Returns:
            HealthResponse: Current health status of the application
        """
        try:
            # Check database status
            if get_database_status:
                db_status = await get_database_status()
            else:
                db_status = "unavailable"
            
            # Calculate uptime
            uptime = time.time() - app_start_time
            
            return HealthResponse(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                version="1.0.0",
                database=db_status,
                uptime_seconds=round(uptime, 2)
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable"
            )
    
    # Root endpoint
    @app.get(
        "/",
        tags=["root"],
        summary="Root Endpoint",
        description="Welcome message and API information"
    )
    async def root():
        """Root endpoint with basic API information."""
        return {
            "message": "Task Management API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    
    logger.info("FastAPI application configured successfully")
    return app

# Create the application instance
app = create_application()

# Development server runner
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )