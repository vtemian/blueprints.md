# core.database

Set up database configuration and connection management for the task management API.

Dependencies: sqlalchemy, sqlalchemy.orm

Requirements:
- Create SQLAlchemy database engine with configurable database URL
- Set up database session management with proper scoping
- Create declarative base class for all models to inherit from
- Include database initialization function to create all tables
- Add dependency function for FastAPI to get database sessions
- Support both SQLite for development and PostgreSQL for production

Configuration:
- Database URL should be configurable via environment variable
- Use connection pooling for production databases
- Enable SQL query logging in development mode
- Set proper database session timeouts and connection limits

Additional Notes:
- Use SQLAlchemy 2.0+ async patterns if needed for better performance
- Implement proper session cleanup with try/finally blocks
- Add health check function to verify database connectivity
- Consider adding database migration support for future schema changes
- Include error handling for database connection failures