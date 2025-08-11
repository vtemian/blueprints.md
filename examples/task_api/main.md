# main

Project setup and configuration for the FastAPI Task Management API.

Dependencies: fastapi, uvicorn, sqlalchemy, pydantic, python-dotenv

Project Setup:
- Create a FastAPI-based task management API
- Set up proper project structure with models, API routes, and core functionality
- Configure development environment with hot reloading
- Include database setup and configuration
- Provide development and production server configurations

Development Environment:
- Use uvicorn for development server with auto-reload
- Default server configuration: host=0.0.0.0, port=8000
- Support environment variable configuration (.env file)
- Include comprehensive logging setup
- Hot reload enabled for development

Makefile Commands:
- `make install` - Install production dependencies
- `make install-dev` - Install development dependencies including testing tools  
- `make run` - Start the development server
- `make dev` - Start with auto-reload enabled
- `make test` - Run the test suite
- `make clean` - Clean up temporary files and caches

Project Structure:
- app.py - Main FastAPI application with middleware and routing
- models/ - SQLAlchemy database models (User, Task)
- api/ - API route handlers (users, tasks)  
- core/ - Core functionality (database setup, configuration)
- main.py - Server startup script

Dependencies to Install:
- fastapi - Web framework
- uvicorn - ASGI server for development and production
- sqlalchemy - Database ORM
- pydantic - Data validation and serialization
- python-dotenv - Environment variable management

Additional Notes:
- Include health check endpoint for monitoring
- Support graceful shutdown handling
- Configure CORS for frontend integration
- Include comprehensive error handling and logging
- Environment-specific configuration (development/production)