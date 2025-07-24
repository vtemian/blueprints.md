# api.tasks
Task management API endpoints

deps: @..core.database[get_db]; @..models.task[Task]; @..models.user[User]

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[dict])
async get_tasks(db: Session = Depends(get_db)) -> List[dict]:
  # Get all tasks
  
@router.post("/", status_code=status.HTTP_201_CREATED)
async create_task(title: str, description: str = None, user_id: int = 1, db: Session = Depends(get_db)) -> dict:
  # Create new task
  
@router.get("/{task_id}")
async get_task(task_id: int, db: Session = Depends(get_db)) -> dict:
  # Get specific task by ID
  
@router.put("/{task_id}")
async update_task(task_id: int, title: str = None, description: str = None, db: Session = Depends(get_db)) -> dict:
  # Update task details
  
@router.patch("/{task_id}/complete")
async complete_task(task_id: int, db: Session = Depends(get_db)) -> dict:
  # Mark task as completed
  
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
  # Delete task

notes: add pagination for get_tasks, implement user authentication, add input validation