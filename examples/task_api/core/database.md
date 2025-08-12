# core.database

Database connection and session management.

Dependencies: sqlalchemy, alembic

Requirements:
- Database connection setup with SQLAlchemy
- Session management with proper cleanup
- Database URL from environment variables
- Connection pooling configuration
- Health check functionality
- Migration support with Alembic
- Dependency injection for FastAPI (get_db function)