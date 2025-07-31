# blueprints.md 🏗️

Write markdown. Get production code. It's that simple.

```bash
# Write this 👇
📄 api/tasks.md
```
```markdown
# api.tasks
Task CRUD operations

router = APIRouter("/tasks")

get_tasks() -> List[Task]
create_task(task: TaskCreate) -> Task
update_task(id: int, task: TaskUpdate) -> Task
```

```bash
# Run this 🚀
blueprints generate api/tasks.md

# Get this ✨
📄 api/tasks.py (200+ lines of production FastAPI code)
```

## What's happening here? 🤔

You describe your code architecture in markdown. Claude AI writes the implementation. No more boilerplate. Just design.

```
📂 my-app/
┣ 📄 main.md          # Your app blueprint
┣ 📂 models/
┃   ┣ 📄 user.md      # User model blueprint
┃   ┗ 📄 task.md      # Task model blueprint
┣ 📂 api/
┃   ┣ 📄 users.md     # User endpoints blueprint
┃   ┗ 📄 tasks.md     # Task endpoints blueprint
┗ 📄 database.md      # Database setup blueprint

# One command generates everything 🎯
$ blueprints generate-project my-app/

✨ Generated 6 Python files + Makefile
🚀 Run 'make setup && make run' to start
```

## Get Started in 30 Seconds ⚡

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY="your-key"

# 2. Install
pip install blueprints-md  # coming soon!
# or clone & install locally
git clone https://github.com/yourusername/blueprints.md
cd blueprints.md && uv sync

# 3. Generate something cool
blueprints generate-project examples/task_api/
cd examples/task_api && make run

# 🎉 You now have a full FastAPI app running!
```

## Why blueprints.md? 🤷

**The old way:** Write 500 lines of boilerplate 😩
```python
class TaskService:
    def __init__(self, db: Database):
        self.db = db
    
    async def create_task(self, task_data: TaskCreate, user_id: int):
        # 50+ lines of validation, error handling, DB ops...
        # More boilerplate...
        # Even more boilerplate...
```

**The blueprints way:** Describe what you want 😎
```markdown
# services.task
Task management service

TaskService:
  - create_task(task_data: TaskCreate, user_id: int) -> Task
  - get_user_tasks(user_id: int) -> List[Task]
```

Claude writes all the boring stuff. You focus on architecture.

## Show Me The Magic 🪄

### Single File Generation
```bash
# Got a blueprint? Generate the code!
blueprints generate api/users.md

# Want JavaScript instead? 
blueprints generate api/users.md --language javascript

# Need to see what's happening?
blueprints generate api/users.md -v
```

### Full Project Generation
```bash
# Turn a folder of blueprints into a working app
blueprints generate-project my-project/

# What you get:
✅ All source files generated
✅ Imports figured out automatically  
✅ Dependencies resolved in the right order
✅ Makefile with setup/run/test commands
✅ Production-ready code with error handling

# It just works 🎉
cd my-project && make run
```

## Blueprint Format 📝

Super simple. Like writing pseudocode but cleaner:

```markdown
# module.name
What this module does

deps: @.other.module[Thing]  # only for your blueprints!

MyClass:
  - do_stuff(param: str) -> bool
  - count: int = 0

my_function(x: int) -> str:
  """One line doc"""
  # any implementation notes

CONSTANT: int = 42
```

**The cool part:** Claude figures out all the imports. You don't write `import os` or `from fastapi import ...`. Just focus on your design. 🧠

## Real Example That Actually Works 🚀

Check out `examples/task_api/` - a complete FastAPI app:

```
📂 task_api/
┣ 📄 main.md              # Entry point & setup
┣ 📄 app.md               # FastAPI app config
┣ 📂 models/
┃   ┣ 📄 user.md          # User model with auth
┃   ┗ 📄 task.md          # Task model with relations
┣ 📂 core/
┃   ┗ 📄 database.md      # Async SQLAlchemy setup
┗ 📂 api/
    ┣ 📄 users.md         # User CRUD + JWT auth
    ┗ 📄 tasks.md         # Task CRUD endpoints
```

**One command:**
```bash
blueprints generate-project examples/task_api/
```

**You get:**
- ✅ Complete async FastAPI app
- ✅ SQLAlchemy models with relationships  
- ✅ JWT authentication
- ✅ Full CRUD operations
- ✅ Error handling everywhere
- ✅ Type hints & validation
- ✅ Makefile to run it all

```bash
cd examples/task_api
make setup  # Install deps
make run    # Start server
# 🎊 http://localhost:8000/docs
```

## The Magic Behind It ✨

**generate vs generate-project:**

🔹 **`generate`** - For single files with context
```bash
blueprints generate api/tasks.md
# → Creates tasks.py with ALL dependencies included
# → One API call, full context awareness
# → Perfect when updating one component
```

🔹 **`generate-project`** - For entire projects  
```bash
blueprints generate-project my-app/
# → Creates all files in dependency order
# → One API call per file (efficient!)
# → Generates Makefile automatically
# → Just works™️
```

## Config & Options ⚙️

```bash
# Required
export ANTHROPIC_API_KEY="your-key"

# Optional tweaks
export BLUEPRINTS_MODEL="claude-3-5-sonnet-20241022"  # or newer!
export BLUEPRINTS_LANGUAGE="python"                   # or javascript, go, etc
export BLUEPRINTS_MAX_TOKENS="4000"                   # for big files
export BLUEPRINTS_TEMPERATURE="0.0"                   # keep it deterministic
```

## Hacking on blueprints.md 🛠️

We eat our own dog food! The entire CLI is built with blueprints:

```bash
# Check out the blueprints
ls src/blueprints/*.md

# Make changes to a blueprint
vim src/blueprints/generator.md

# Regenerate the code
blueprints generate-project src/blueprints/

# Test it out
uv run pytest
```

## What People Are Saying 💬

"Wait, so I just write markdown and get a whole app?" - Everyone, first time

"This is like having a senior dev who never gets tired of writing boilerplate" - Happy user

"My blueprints folder is smaller than my old __init__.py files" - True story

## FAQ 🤔

**Q: Does this replace developers?**  
A: Nope! It replaces boilerplate. You still design the architecture.

**Q: What languages does it support?**  
A: Python, JavaScript, TypeScript, Go, and more. Claude's pretty smart.

**Q: Can I use my own models?**  
A: If it speaks the Anthropic API, it works!

**Q: Is the generated code any good?**  
A: Check out the examples. It's production-ready with error handling, types, and docs.

## Get Started Now! 🚀

```bash
export ANTHROPIC_API_KEY="your-key"
pip install blueprints-md  # soon!
blueprints generate-project my-awesome-app/
```

---

Built with ❤️ by developers who got tired of writing the same code over and over.

Want to contribute? PRs welcome! Just remember to update the blueprints, not the generated code 😉
