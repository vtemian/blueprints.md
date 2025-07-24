# main
Task Management API - A FastAPI-based REST API for managing tasks and users

## Project Overview
A complete task management system built with FastAPI, featuring user authentication, task CRUD operations, and SQLite database integration.

## Third-party Dependencies
- fastapi>=0.104.0  # Web framework
- uvicorn[standard]>=0.24.0  # ASGI server
- sqlalchemy>=2.0.0  # Database ORM
- aiosqlite>=0.19.0  # Async SQLite driver
- bcrypt>=4.0.0  # Password hashing
- python-jose[cryptography]>=3.3.0  # JWT tokens
- python-multipart>=0.0.6  # Form data parsing
- pydantic>=2.0.0  # Data validation

## Development Dependencies
- pytest>=7.0.0  # Testing framework
- pytest-asyncio>=0.21.0  # Async testing
- httpx>=0.25.0  # HTTP client for testing
- black>=23.0.0  # Code formatting
- mypy>=1.5.0  # Type checking

## Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=sqlite:///./tasks.db
export SECRET_KEY=your-secret-key-here
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Running the Application
```bash
# Development server
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints
- GET / - Health check
- GET /health - Detailed health status
- POST /users/register - User registration
- POST /users/login - User authentication
- GET /tasks - List user tasks
- POST /tasks - Create new task
- PUT /tasks/{id} - Update task
- DELETE /tasks/{id} - Delete task

## Project Structure
- app.py - FastAPI application entrypoint and configuration
- api/ - API route handlers
  - tasks.py - Task management endpoints
  - users.py - User authentication endpoints
- models/ - Database models
  - task.py - Task data model
  - user.py - User data model
- core/ - Core functionality
  - database.py - Database connection and setup

## Architecture Notes
- Uses JWT tokens for authentication
- SQLite database with SQLAlchemy ORM
- Async/await pattern throughout
- Pydantic models for request/response validation
- Modular router-based API structure

notes: RESTful API design, secure authentication, comprehensive error handling, async database operations