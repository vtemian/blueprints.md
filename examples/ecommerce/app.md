# app

Create the main FastAPI application for a comprehensive e-commerce platform with user management, product catalog, shopping cart, order processing, and payment integration.

Dependencies: fastapi, @./api/products, @./api/cart, @./api/auth, @./api/orders, @./api/payments, @./api/reviews, @./core/database

Requirements:
- Set up FastAPI application with comprehensive metadata and documentation
- Include CORS middleware configured for production and development
- Add all API routers with appropriate prefixes and tags
- Implement application lifecycle management (startup/shutdown events)
- Add comprehensive error handling and exception handlers
- Include health check endpoints for monitoring and load balancers
- Set up request/response logging for debugging and analytics

Application Configuration:
- Configure OpenAPI documentation with detailed descriptions
- Set up API versioning with /api/v1 prefix
- Enable automatic request validation and serialization
- Add middleware for security headers and rate limiting
- Configure database connection pooling and session management

Error Handling:
- Global HTTP exception handler with consistent error responses
- Custom validation error formatting for user-friendly messages
- Internal server error handling with proper logging
- Request timeout and rate limit error handling

Production Considerations:
- Make CORS origins configurable via environment variables
- Add comprehensive logging configuration
- Include monitoring and metrics endpoints
- Support graceful shutdown with proper cleanup
- Configure security middleware for production deployment