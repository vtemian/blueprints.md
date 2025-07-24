# blueprints.md

blueprints.md allows developers to write concise markdown "blueprints" that describe their code architecture, then automatically generate the complete implementation using Claude AI. Instead of writing boilerplate code, you focus on design and let AI handle the implementation details.

## Quick Start

1. **Set up your Anthropic API key:**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

2. **Install blueprints.md:**
   ```bash
   uv sync
   # or
   pip install -e .
   ```

3. **Generate code from a blueprint:**
   ```bash
   # Single file (with dependency context)
   blueprints generate examples/task_api/api/tasks.md
   
   # Entire project with Makefile (auto-detects main.md)
   blueprints generate-project examples/task_api/
   ```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/blueprints.md.git
cd blueprints.md

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Usage

### Generate code from a blueprint

```bash
# Generate single blueprint (with dependency context)
blueprints generate path/to/blueprint.md

# Generate with specific output path
blueprints generate blueprint.md -o output.py

# Generate in a different language
blueprints generate blueprint.md --language javascript

# Force overwrite existing files
blueprints generate blueprint.md --force

# Verbose output shows dependency resolution
blueprints generate blueprint.md -v
```

### Generate entire project

```bash
# Generate entire project with dependencies and Makefile
# Auto-detects main.md in directory
blueprints generate-project examples/task_api/

# Or specify main.md directly
blueprints generate-project examples/task_api/main.md

# Verbose output shows generation order
blueprints generate-project examples/task_api/ -v
```

### Other commands

```bash
# Initialize a new blueprint
blueprints init my_module

# Discover blueprints in a directory
blueprints discover src/
```

## Blueprint Format

See `BLUEPRINTS_SPEC.md` for the complete specification. The compact format reduces file size by ~75%:

```markdown
# module.name
Brief description of what this module does

deps: @.other.blueprint[Component]

MyClass:
  - method_name(param: type) -> return_type  # comment
  - property: type

my_function(param: type = default) -> return_type:
  """Docstring"""
  # implementation notes

CONSTANT_NAME: type = value

notes: implementation detail 1, performance note, future enhancement
```

**Key Feature**: Only blueprint references (with `@` prefix) need to be specified. Standard library imports (`typing`, `datetime`, `os`) and third-party packages (`fastapi`, `sqlalchemy`) are automatically inferred and imported by Claude during generation.

## How It Works

1. **Write Blueprints** - Create concise `.md` files describing your code structure
2. **Define Dependencies** - Reference other blueprints with `@` syntax for modular design  
3. **Generate Code** - Run `blueprints generate-project` to create complete implementations
4. **Get Production Code** - Receive fully functional code with imports, error handling, and documentation

The system uses Claude AI to understand your blueprint specifications and generate idiomatic code in your target language, automatically inferring dependencies and following best practices.

## Example: Task Management API

The `examples/task_api/` directory contains a complete FastAPI application:

```
task_api/
├── main.md              # Project documentation and setup
├── app.md               # FastAPI application entrypoint
├── models/
│   ├── user.md          # User model
│   └── task.md          # Task model  
├── core/
│   └── database.md      # Database setup
└── api/
    ├── users.md         # User endpoints
    └── tasks.md         # Task endpoints
```

Generate the entire project with Makefile:
```bash
blueprints generate-project examples/task_api/ -v
```

This creates all Python files alongside the blueprints plus a Makefile with:
- `make setup` - Install dependencies
- `make run` - Start the application  
- `make dev` - Development server with reload
- `make test` - Run tests

**What gets generated:**
- Complete FastAPI application with authentication
- SQLAlchemy models with relationships
- API routes with validation and error handling
- Database setup with async support
- JWT token authentication
- Comprehensive error handling
- Type hints throughout
- Production-ready structure

## Command Comparison

| Command | Files Generated | API Calls | Use Case |
|---------|----------------|-----------|----------|
| `generate` | Single file | 1 call with all dependencies as context | Generate one file with full context |
| `generate-project` | All files in dependency order | 1 call per blueprint | Generate entire project efficiently |

### `generate-project` creates:
- One API call per blueprint (7 total for task_api)
- Dependencies resolved automatically  
- Files generated alongside blueprint files (.py next to .md)
- Complete working FastAPI application
- **Makefile with setup, run, and development commands**

### `generate` creates:
- Single file with all blueprint dependencies as context
- One API call with full context
- Perfect for generating one component that uses others

## Configuration

Environment variables:
- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `BLUEPRINTS_MODEL` - Claude model to use (default: claude-3-5-sonnet-20241022)
- `BLUEPRINTS_LANGUAGE` - Default output language (default: python)
- `BLUEPRINTS_MAX_TOKENS` - Max tokens for generation (default: 4000)
- `BLUEPRINTS_TEMPERATURE` - Temperature for generation (default: 0.0)

## Why Choose blueprints.md?

**Traditional Development:**
```python
# You write hundreds of lines of boilerplate
class TaskService:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_task(self, task_data: TaskCreate, user_id: int):
        # 50+ lines of implementation...
```

**blueprints.md Approach:**
```markdown
# services.task
Task management service with CRUD operations

TaskService:
  - create_task(task_data: TaskCreate, user_id: int) -> Task
  - get_user_tasks(user_id: int) -> List[Task]
  - update_task(task_id: int, updates: TaskUpdate) -> Task
```

**Result:** Complete, production-ready implementation generated automatically with proper error handling, validation, and database operations.

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black .

# Type checking
uv run mypy .
```

## Contributing

blueprints.md uses itself for development! The entire codebase is documented with blueprints in `src/blueprints/*.md`. To contribute:

1. Modify the relevant blueprint files
2. Run `blueprints generate-project src/blueprints/` to regenerate code
3. Test your changes
4. Submit a pull request

This ensures all code changes are properly documented and architecture is maintained.

## Example Output

```bash
$ blueprints generate examples/task_api/api/tasks.md -v

Generating code from blueprint: examples/task_api/api/tasks.md
  Module: api.tasks
  Components: 6
  Dependencies: 3 blueprints
    - models.task
    - models.user
    - core.database

✓ Generated code saved to: examples/task_api/api/tasks.py
  Language: python
  Size: 2847 bytes
```

```bash
$ blueprints generate-project examples/task_api/ -v

Generating project from blueprint: examples/task_api/main.md
Files will be generated alongside blueprint files
  Main module: main
  Total blueprints: 7
  Generation order:
    1. models.user
    2. core.database  
    3. models.task
    4. api.users
    5. api.tasks
    6. app
    7. main

✓ Generated 7 files:
  models.user -> examples/task_api/models/user.py
  core.database -> examples/task_api/core/database.py
  models.task -> examples/task_api/models/task.py
  api.users -> examples/task_api/api/users.py
  api.tasks -> examples/task_api/api/tasks.py
  app -> examples/task_api/app.py
  Makefile -> examples/task_api/Makefile
  
✓ Generated Makefile with setup and run commands
```
