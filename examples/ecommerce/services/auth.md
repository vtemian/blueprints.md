# services.auth

Authentication service with JWT tokens and password security.

Dependencies: fastapi, pyjwt, passlib, redis, @../models/user, @../core/database

Requirements:
- JWT token generation and validation
- Secure password hashing with bcrypt
- User authentication with email/password
- Token blacklisting for secure logout
- Refresh token management
- Password reset with email tokens
- FastAPI dependencies for current user

Security:
- Strong JWT secrets from environment
- Token blacklisting prevents replay attacks
- Rate limiting for auth attempts
- Redis-based session management