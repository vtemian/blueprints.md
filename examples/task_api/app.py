from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.tasks import router as tasks_router
from api.users import router as users_router
from core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Lifecycle manager for startup/shutdown events."""
    init_db()
    yield


app = FastAPI(
    title="Task Management API",
    description="A simple task management system with user authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(tasks_router, prefix="/api/v1", tags=["tasks"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])


@app.get("/", tags=["health"])
async def root() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, str]:
    """Detailed health check with database connectivity status."""
    try:
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": str(e)
        }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)