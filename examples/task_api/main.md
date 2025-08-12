# main

FastAPI task management API setup and configuration.

Dependencies: fastapi, uvicorn, sqlalchemy, pydantic, python-dotenv, @./app, @./models/user, @./models/task, @./api/users, @./api/tasks, @./core/database

Requirements:
- FastAPI app setup with proper project structure
- Environment configuration with .env support
- Development server with hot reload
- Health check endpoint
- Database setup and configuration
- CORS middleware for frontend integration

Development:
- Use uvicorn for dev server (host=0.0.0.0, port=8000)
- Enable hot reload for development
- Comprehensive error handling and logging
- Graceful shutdown handling