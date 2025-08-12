# api.users

User management API endpoints with authentication.

Dependencies: fastapi, jwt, passlib, @../models/user, @../core/database

Requirements:
- POST /register for user registration with email validation
- POST /login for authentication returning JWT token
- GET /me for current user profile
- PUT /me for profile updates
- POST /password-reset for password reset flow
- JWT token validation and user authentication
- Input validation with Pydantic models
- Proper HTTP status codes and error handling