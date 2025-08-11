import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    CORS_ORIGINS: list[str] = ["*"]
    TRUSTED_HOSTS: list[str] = ["*"]
    RATE_LIMIT: str = "100/minute"
    ENV: str = "development"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

class RequestIDMiddleware:
    """Middleware to add request ID header for tracing."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        request_id = str(uuid.uuid4())
        scope["state"] = {"request_id": request_id}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((b"X-Request-ID", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup/shutdown events."""
    logger.info("Starting up application...")
    # Add startup logic here (e.g. database connections)
    
    yield
    
    logger.info("Shutting down application...")
    # Add cleanup logic here

async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global error handler."""
    logger.exception("Unhandled error", extra={"request_id": request.state.request_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings()
    
    app = FastAPI(
        title="API App",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENV == "development" else None
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Error handlers
    app.exception_handler(Exception)(error_handler)

    # Health check
    @app.get("/health", status_code=status.HTTP_200_OK)
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)