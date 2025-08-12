# app

Main FastAPI application with middleware and routing.

Dependencies: fastapi, @./api/users, @./api/tasks, @./core/database

Requirements:
- FastAPI app instance with proper configuration
- CORS middleware for frontend integration
- Include API routers for users and tasks
- Global exception handling
- Request/response logging middleware
- Application lifespan management
- Health check endpoint at /health