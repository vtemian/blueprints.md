# core.database

Set up database configuration, connection management, and declarative base for the e-commerce platform with SQLAlchemy ORM.

Dependencies: sqlalchemy, sqlalchemy.orm, @../models/user, @../models/product, @../models/order, @../models/cart

Requirements:
- Create SQLAlchemy database engine with configurable connection string
- Set up session management with proper scoping and lifecycle
- Create declarative base class for all models to inherit from
- Include database initialization function to create all tables
- Add FastAPI dependency function for database session injection
- Support both PostgreSQL for production and SQLite for development

Database Configuration:
- Make database URL configurable via environment variables
- Use connection pooling for production with appropriate limits
- Enable SQL query logging in development mode
- Set proper connection timeouts and retry mechanisms
- Configure database-specific optimizations (indexes, constraints)

Session Management:
- Implement proper session lifecycle with automatic cleanup
- Use dependency injection pattern for FastAPI routes
- Handle database transactions with proper rollback on errors
- Support both sync and async database operations if needed
- Include session-per-request pattern for web applications

Additional Features:
- Add database health check function for monitoring
- Include database migration support preparation
- Support multiple database environments (dev, test, prod)
- Add comprehensive error handling for connection failures
- Include database backup and restore utilities preparation

Performance Considerations:
- Configure connection pooling with appropriate settings
- Use lazy loading strategies for relationships
- Implement query optimization and indexing strategies
- Add database performance monitoring hooks
- Support read/write splitting for high-load scenarios