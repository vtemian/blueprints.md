# app
FastAPI application entrypoint and configuration

deps: @.api.tasks[router as tasks_router]; @.api.users[router as users_router]; @.core.database[init_db]

app = FastAPI(
    title="Task Management API",
    description="A simple task management system with user authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tasks_router, prefix="/api/v1", tags=["tasks"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])

@app.on_event("startup")
async startup_event():
  """Initialize database tables and connections on startup."""
  # Initialize database
  
@app.on_event("shutdown") 
async shutdown_event():
  """Clean up resources on shutdown."""
  # Close database connections
  
@app.get("/")
async root() -> dict[str, str]:
  """Basic health check endpoint."""
  # Return API status and version
  
@app.get("/health")
async health_check() -> dict[str, str]:
  """Detailed health check with database connectivity status."""
  # Check database connection
  # Return comprehensive health status

@app.exception_handler(HTTPException)
async http_exception_handler(request: Request, exc: HTTPException):
  """Custom HTTP exception handler."""
  # Log error and return formatted response

@app.exception_handler(Exception)
async general_exception_handler(request: Request, exc: Exception):
  """Global exception handler for unhandled errors."""
  # Log unexpected errors
  # Return generic error response

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)

notes: CORS configured for development, comprehensive error handling, startup/shutdown lifecycle management, API versioning with prefix