# app

Create the main FastAPI application with routing, middleware, and lifecycle management.

Dependencies: fastapi, @./api/tasks, @./api/users, @./core/database

Requirements:
- Create FastAPI application instance with proper metadata (title, description, version)
- Include API documentation endpoints (/docs, /redoc)
- Add CORS middleware for cross-origin requests
- Include task and user routers with /api/v1 prefix
- Implement application startup and shutdown event handlers
- Add basic health check endpoints for monitoring

Application Setup:
- Configure CORS to allow appropriate origins (configurable for production)
- Set up API versioning with /api/v1 prefix for all endpoints
- Include proper error handling middleware
- Add request/response logging for debugging
- Configure OpenAPI documentation with comprehensive descriptions

Lifecycle Management:
- Initialize database tables on startup
- Close database connections on shutdown
- Include health check endpoint that verifies database connectivity
- Add basic root endpoint that returns API status and version

Additional Notes:
- Make CORS origins configurable via environment variables
- Include comprehensive error handlers for HTTP exceptions
- Add request ID tracking for better debugging
- Consider adding rate limiting middleware for production
- Include graceful shutdown handling for production deployments