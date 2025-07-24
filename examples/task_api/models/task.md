# models.task
Task data model for the task management system

deps: @.user[User]

Task:
  __tablename__ = "tasks"
  
  - id: Column[Integer] = primary_key=True
  - title: Column[String(200)] = nullable=False
  - description: Column[String] = nullable=True
  - completed: Column[Boolean] = default=False
  - created_at: Column[DateTime] = default=datetime.utcnow
  - updated_at: Column[DateTime] = default=datetime.utcnow, onupdate=datetime.utcnow
  - user_id: Column[Integer] = ForeignKey("users.id")
  
  - user: relationship[User] = back_populates="tasks"
  
  - mark_completed() -> None
  - mark_incomplete() -> None
  - update_title(title: str) -> None
  - to_dict() -> dict[str, any]

notes: add validation for title length, index on user_id and completed status