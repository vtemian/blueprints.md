# requirements
Python dependencies for the task management API

deps: # No dependencies needed for this file

# FastAPI and ASGI server
fastapi_requirement: str = "fastapi>=0.104.0"
uvicorn_requirement: str = "uvicorn[standard]>=0.24.0"

# Database
sqlalchemy_requirement: str = "sqlalchemy>=2.0.0"
sqlite_requirement: str = "aiosqlite>=0.19.0"  # For async SQLite

# Password hashing
bcrypt_requirement: str = "bcrypt>=4.0.0"

# Development
pytest_requirement: str = "pytest>=7.0.0"
pytest_asyncio_requirement: str = "pytest-asyncio>=0.21.0"

generate_requirements_txt() -> str:
  """Generate requirements.txt content"""
  # Return formatted requirements

notes: pin versions for production, add optional dev dependencies, consider using poetry