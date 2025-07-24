# models.user
User data model for authentication and task ownership

User:
  __tablename__ = "users"
  
  - id: Column[Integer] = primary_key=True
  - username: Column[String(50)] = unique=True, nullable=False
  - email: Column[String(100)] = unique=True, nullable=False
  - hashed_password: Column[String(255)] = nullable=False
  - is_active: Column[Boolean] = default=True
  - created_at: Column[DateTime] = default=datetime.utcnow
  
  - tasks: relationship["Task"] = back_populates="user"
  
  - set_password(password: str) -> None
  - verify_password(password: str) -> bool
  - to_dict() -> dict[str, any]  # exclude password

notes: add unique indexes on username and email, use bcrypt for password hashing