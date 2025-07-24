# main
FastAPI application entrypoint for task management API

deps: fastapi[FastAPI]; uvicorn; @.api.tasks[router as tasks_router]; @.api.users[router as users_router]; @.core.database[init_db]

app = FastAPI(
    title="Task Management API",
    description="A simple task management system",
    version="1.0.0"
)

app.include_router(tasks_router)
app.include_router(users_router)

@app.on_event("startup")
async startup_event():
  # Initialize database
  
@app.get("/")
async root() -> dict[str, str]:
  # Health check endpoint
  
@app.get("/health")
async health_check() -> dict[str, str]:
  # Detailed health check

notes: add CORS middleware, setup logging, add exception handlers