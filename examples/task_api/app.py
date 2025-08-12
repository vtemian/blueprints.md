import logging
import os
from contextlib import asynccontextmanager
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
TRUSTED_HOSTS = os.getenv("TRUSTED_HOSTS", "").split(",")
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to each request for tracking."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            logger.exception(f"Error processing request {request_id}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "request_id": request_id}
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting up application...")
    yield
    # Shutdown
    logger.info("Shutting down application gracefully...")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(lifespan=lifespan)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=TRUSTED_HOSTS
    )

    # Add request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Add rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers={"Retry-After": str(exc.retry_after)}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception(f"Unhandled error for request {request_id}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id
            }
        )

    return app

# Create application instance
app = create_app()

@app.get("/health")
@limiter.limit(RATE_LIMIT)
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}