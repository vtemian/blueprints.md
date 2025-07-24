# api.users
User management API endpoints

deps: fastapi[APIRouter, HTTPException, Depends, status]; sqlalchemy.orm[Session]; typing[List]; @..core.database[get_db]; @..models.user[User]

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[dict])
async get_users(db: Session = Depends(get_db)) -> List[dict]:
  # Get all users (excluding passwords)
  
@router.post("/", status_code=status.HTTP_201_CREATED)
async create_user(username: str, email: str, password: str, db: Session = Depends(get_db)) -> dict:
  # Create new user account
  
@router.get("/{user_id}")
async get_user(user_id: int, db: Session = Depends(get_db)) -> dict:
  # Get specific user by ID
  
@router.get("/{user_id}/tasks")
async get_user_tasks(user_id: int, db: Session = Depends(get_db)) -> List[dict]:
  # Get all tasks for a specific user

notes: add email validation, implement proper authentication, add rate limiting