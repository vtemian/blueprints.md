# blueprints.md

A markdown-to-code generation system that uses Claude API to generate source code from blueprint specifications.

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
   
   # Entire project (separate API calls)
   blueprints generate-project examples/task_api/main.md
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
# Generate entire project with dependencies (separate API calls)
# Files are generated alongside blueprint files
blueprints generate-project examples/task_api/main.md

# Verbose output shows generation order
blueprints generate-project examples/task_api/main.md -v
```

### Other commands

```bash
# Initialize a new blueprint
blueprints init my_module

# Validate a blueprint
blueprints validate my_module.md

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

## Example: Task Management API

The `examples/task_api/` directory contains a complete FastAPI application:

```
task_api/
├── main.md              # FastAPI app entrypoint
├── models/
│   ├── user.md          # User model
│   └── task.md          # Task model  
├── core/
│   └── database.md      # Database setup
└── api/
    ├── users.md         # User endpoints
    └── tasks.md         # Task endpoints
```

Generate the entire project:
```bash
blueprints generate-project examples/task_api/main.md -v
```

## Command Comparison

| Command | Files Generated | API Calls | Use Case |
|---------|----------------|-----------|----------|
| `generate` | Single file | 1 call with all dependencies as context | Generate one file with full context |
| `generate-project` | All files in dependency order | 1 call per blueprint | Generate entire project efficiently |

### `generate-project` creates:
- One API call per blueprint (6 total)
- Dependencies resolved automatically  
- Files generated alongside blueprint files (.py next to .md)
- Complete working FastAPI application

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

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black .

# Type checking
uv run mypy .
```

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
$ blueprints generate-project examples/task_api/main.md -v

Generating project from blueprint: examples/task_api/main.md
Files will be generated alongside blueprint files
  Main module: main
  Total blueprints: 6
  Generation order:
    1. models.user
    2. core.database  
    3. models.task
    4. api.users
    5. api.tasks
    6. main

✓ Generated 6 files:
  models.user -> examples/task_api/models/user.py
  core.database -> examples/task_api/core/database.py
  models.task -> examples/task_api/models/task.py
  api.users -> examples/task_api/api/users.py
  api.tasks -> examples/task_api/api/tasks.py
  main -> examples/task_api/main.py
```