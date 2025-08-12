# Task API Project

A modern FastAPI-based task management API with user authentication and task management capabilities.

## Project Structure

```
task_api/
├── app.py              # Main FastAPI application entry point
├── core/
│   └── database.py     # Database configuration and session management
├── models/
│   ├── user.py         # User model with authentication
│   └── task.py         # Task model with user relationships
├── api/
│   ├── users.py        # User authentication and profile endpoints
│   └── tasks.py        # Task CRUD endpoints
├── requirements.txt    # Production dependencies
└── requirements-dev.txt # Development dependencies
```

## Development Setup

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### Environment Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite:///./app.db
# DATABASE_URL=postgresql://user:password@localhost/taskapi

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Running the Application

**Development Mode:**
```bash
# With hot reload
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Or using the make command
make dev
```

**Production Mode:**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Database Setup

The application will automatically create SQLite tables on first run. For production PostgreSQL:

1. Install PostgreSQL
2. Create database: `createdb taskapi`
3. Update `DATABASE_URL` in `.env`
4. Run migrations if using Alembic

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_users.py
```

## Development Best Practices

### Code Quality
- Use `black` for code formatting
- Use `flake8` for linting
- Use `mypy` for type checking
- Write tests for all endpoints

### Security
- Never commit `.env` files
- Use strong JWT secret keys in production
- Implement rate limiting for production
- Use HTTPS in production

### Database
- Use migrations for schema changes
- Implement database connection pooling
- Add database health checks
- Backup strategies for production

## Production Deployment

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Production)
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Strong random key
- `ALLOWED_ORIGINS`: Frontend domain(s)
- `DEBUG=false`

## Monitoring & Logging

- Application logs to stdout/stderr
- Health check endpoint: `/health`
- Database health check: `/health/db`
- Metrics endpoint (if implemented): `/metrics`

## License

MIT License - see LICENSE file for details.