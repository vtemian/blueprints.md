import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger(__name__)

class Settings:
    CORS_ORIGINS: list[str] = ["*"]
    TRUSTED_HOSTS: list[str] = ["*"] 
    RATE_LIMIT: str = "100/minute"
    ENV: str = "development"
    
    def __init__(self):
        self.model_config = {
            "env_file": ".env",
            "case_sensitive": True
        }

class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request_id = str(uuid.uuid4())
        scope["state"] = {"request_id": request_id}

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append((b"X-Request-ID", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped_send)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up application")
    yield
    logger.info("Shutting down application")

def create_app() -> FastAPI:
    settings = Settings()
    
    app = FastAPI(
        title="FastAPI Application",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENV == "development" else None
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS
    )

    app.add_middleware(RequestIDMiddleware)

    @app.get("/health", status_code=status.HTTP_200_OK)
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app()

if __name__ == "__main__":
    import sys
    sys.exit("Run with a WSGI/ASGI server")