# api.users

Build user management and authentication API endpoints for user registration and login.

Dependencies: fastapi, jwt, bcrypt, @../models/user, @../core/database

Requirements:
- Create FastAPI router with "/users" prefix and "users" tag
- POST /users/register endpoint for new user registration
- POST /users/login endpoint for user authentication
- GET /users/me endpoint to get current authenticated user profile
- PUT /users/me endpoint to update user profile (username, email)
- Include Pydantic schemas for request/response validation
- Implement JWT token generation and validation

Authentication:
- Register endpoint creates new user with hashed password
- Login endpoint validates credentials and returns JWT token
- Protected endpoints require valid JWT token in Authorization header
- Include password strength validation on registration
- Prevent duplicate usernames and emails

Security:
- Hash passwords with bcrypt before storing
- Generate secure JWT tokens with expiration times
- Rate limit login attempts to prevent brute force attacks
- Validate email format and username requirements
- Never return password hashes in API responses

Additional Notes:
- Include proper error handling for authentication failures
- Return consistent error messages for validation issues
- Support token refresh mechanism for long-lived sessions
- Add user account activation via email if needed
- Consider implementing password reset functionality