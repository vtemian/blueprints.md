# api.tasks

Task management API endpoints with CRUD operations.

Dependencies: fastapi, @../models/task, @../models/user, @../core/database

Requirements:
- GET /tasks for listing user tasks with pagination
- POST /tasks for creating new tasks
- GET /tasks/{id} for retrieving specific task
- PUT /tasks/{id} for updating tasks
- DELETE /tasks/{id} for task removal
- Query filtering by completion status
- User ownership validation (users can only access their tasks)
- Pydantic models for request/response validation