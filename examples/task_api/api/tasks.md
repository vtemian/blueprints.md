# api.tasks

Build task management API endpoints for creating, reading, updating, and deleting user tasks.

Dependencies: fastapi, @../models/task, @../models/user, @../core/database

Requirements:
- Create FastAPI router with "/tasks" prefix and "tasks" tag
- GET /tasks endpoint to list all tasks for the authenticated user with pagination
- GET /tasks/{task_id} endpoint to get a specific task by ID (user must own the task)
- POST /tasks endpoint to create a new task for the authenticated user
- PUT /tasks/{task_id} endpoint to update task title, description, or completion status
- DELETE /tasks/{task_id} endpoint to delete a task (user must own the task)
- Include Pydantic schemas for request/response validation

Authentication:
- All endpoints require user authentication
- Users can only access their own tasks (no cross-user access)
- Include proper authorization checks on all task operations

Validation:
- Task creation requires title (non-empty), description is optional
- Task updates should validate field types and constraints
- Return appropriate HTTP status codes (200, 201, 404, 403, 422)
- Include detailed error messages for validation failures

Additional Notes:
- Support pagination with page and per_page query parameters
- Add filtering by completion status (completed=true/false)
- Include task count in list responses
- Use dependency injection for database sessions
- Return consistent JSON response format across all endpoints