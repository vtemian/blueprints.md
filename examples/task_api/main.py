import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings:
    """Application configuration settings."""
    app_name: str = "Task Management API"
    debug: bool = False
    host: str = "0.0.0.0" 
    port: int = 8000

    def __init__(self):
        self.load_env()

    def load_env(self):
        """Load settings from environment variables."""
        self.app_name = os.getenv("APP_NAME", self.app_name)
        self.debug = os.getenv("DEBUG", "").lower() == "true"
        self.host = os.getenv("HOST", self.host)
        self.port = int(os.getenv("PORT", self.port))

class HealthCheck:
    """Health check response model."""
    def __init__(self):
        self.status = "healthy"
        self.version = "1.0.0"

@asynccontextmanager
async def lifespan(app) -> AsyncGenerator:
    """Handles application startup and shutdown events."""
    try:
        logger.info("Starting up application...")
        yield
        logger.info("Shutting down application...")
    except Exception as e:
        logger.error(f"Error during application lifecycle: {e}")
        raise

def create_application():
    """Creates and configures the application."""
    settings = Settings()
    
    class App:
        def __init__(self, title, debug, lifespan):
            self.title = title
            self.debug = debug
            self.lifespan = lifespan
            self.routes = {}

        async def get(self, path):
            """Handle GET request."""
            if path == "/health":
                return HealthCheck()
            elif path == "/":
                return {"message": "Task Management API"}
            return {"error": "Not found", "status_code": 404}

    app = App(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan
    )

    return app

def start_server() -> None:
    """Starts the development server."""
    try:
        settings = Settings()
        
        if not os.path.exists(".env"):
            logger.warning("No .env file found - using default settings")

        # Basic server implementation
        logger.info(f"Starting server on {settings.host}:{settings.port}")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

app = create_application()

if __name__ == "__main__":
    start_server()