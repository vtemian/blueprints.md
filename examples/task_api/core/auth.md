# core.auth

Authentication and authorization utilities.

Dependencies: fastapi, python-jose[cryptography], passlib[bcrypt], python-multipart, @../models/user, @./database

Requirements:
- JWT token generation and validation
- Password hashing with bcrypt
- OAuth2 password bearer authentication
- get_current_user dependency for protected routes
- get_current_active_user with active user validation
- Token refresh capability
- Configurable token expiration from environment
- User authentication with email/username
- Role-based access control support

Security features:
- Secure password hashing with bcrypt
- JWT tokens with HS256 algorithm
- Token expiration and validation
- Optional token refresh mechanism
- Protection against timing attacks
- Secure secret key from environment

Configuration:
- SECRET_KEY from environment (required)
- ALGORITHM (default: HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES (default: 30)
- REFRESH_TOKEN_EXPIRE_DAYS (optional)

Core functions:
- verify_password(plain_password, hashed_password) -> bool
- get_password_hash(password) -> str
- create_access_token(data: dict, expires_delta: timedelta) -> str
- decode_token(token: str) -> dict
- get_current_user(token: Depends(oauth2_scheme), db: Session) -> User
- get_current_active_user(current_user: Depends(get_current_user)) -> User
- authenticate_user(db: Session, email: str, password: str) -> User | None