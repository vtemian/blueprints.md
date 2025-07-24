# Blueprint Specification

A concise format for blueprints that reduces context size by ~75% while maintaining clarity for LLMs.

## Format Overview

```markdown
# module.name
One-line description

deps: @.other.blueprint[Component]

ClassName:
  - method(param: type) -> return_type  # comment
  - property: type

function_name(param: type = default) -> return_type:
  """docstring"""

notes: implementation detail 1, performance note, future enhancement
```

**Key Feature**: Standard library and third-party imports are automatically inferred. Only specify blueprint references with `@` prefix.

## Syntax Rules

### 1. Module Declaration
```markdown
# module.path.name
One-line description
```

### 2. Dependencies (Optional)
```markdown
deps: @.local.blueprint; @..sibling.blueprint[Class1, Function2]
```

Only blueprint references need to be specified. Standard library and third-party imports are automatically inferred by Claude during generation.

Blueprint references use `@` prefix:
- `@.module` - Blueprint in same directory
- `@..module` - Blueprint in parent directory
- `@module.submodule` - Absolute blueprint reference

### 3. Components

#### Classes
```markdown
ClassName(BaseClass):  # inheritance optional
  - method(param: type) -> return_type  # comment
  - property: type
  @classmethod method(cls) -> type
  @staticmethod method() -> type
```

#### Functions
```markdown
function_name(param: type = default) -> return_type:
  """docstring"""
  # behavior notes
```

#### Constants
```markdown
CONSTANT_NAME: type = value
```

### 4. Implementation Notes
```markdown
notes: key point 1, key point 2, key point 3
```

### 5. Advanced Features

#### Type Aliases
```markdown
TypeName = Union[str, int]
```

#### Decorators
```markdown
@decorator
function_name() -> type
```

#### Async Functions
```markdown
async function_name() -> type
```

#### Generators
```markdown
function_name() -> Generator[type, None, None]
```

## Examples

### Example 1: Simple Service
```markdown
# services.email
Email service for sending notifications

deps: smtplib; email.mime.text[MIMEText]; typing[Optional]

EmailService:
  - __init__(host: str, port: int, username: str, password: str)
  - send(to: str, subject: str, body: str) -> bool
  - send_bulk(recipients: list[str], subject: str, body: str) -> dict[str, bool]

notes: use TLS, validate emails, handle SMTP errors, retry failed sends
```

### Example 2: Data Model
```markdown
# models.product
Product data model

deps: sqlalchemy[Column, Integer, String, Float, Boolean]; .base[Base]

Product(Base):
  __tablename__ = "products"
  id: Column[Integer] = primary_key
  name: Column[String(200)] = nullable=False
  price: Column[Float] = nullable=False
  active: Column[Boolean] = default=True
  
  - calculate_discount(percentage: float) -> float
  - apply_tax(rate: float) -> float
  
notes: add indexes on name and active, validate price > 0
```

### Example 3: API Endpoint with Blueprint References
```markdown
# api.auth
Authentication API endpoints

deps: fastapi[APIRouter, HTTPException, Depends]; @..schemas[LoginRequest, TokenResponse]; @..services.auth[AuthService]

router = APIRouter(prefix="/auth")

@router.post("/login") -> TokenResponse:
async login(request: LoginRequest, auth: AuthService = Depends()):
  # validate credentials, generate JWT, return token
  
@router.post("/logout"):
async logout(token: str = Depends(get_current_token)):
  # invalidate token
  
notes: rate limit login, use httponly cookies, implement refresh tokens
```

### Example 4: Complex Types
```markdown
# utils.validators
Data validation utilities

deps: re; typing[Union, Optional, TypeVar, Generic]; pydantic[BaseModel]

T = TypeVar("T")
ValidationResult = tuple[bool, Optional[str]]

Email = NewType("Email", str)

validate_email(email: str) -> ValidationResult:
  # regex check, domain validation
  
class Validator(Generic[T]):
  - __init__(rules: list[Callable[[T], bool]])
  - validate(value: T) -> ValidationResult
  - add_rule(rule: Callable[[T], bool]) -> None
```

## Size Comparison

| Component | Verbose | Compact | Reduction |
|-----------|---------|---------|-----------|
| Module declaration | 3 lines | 2 lines | 33% |
| Dependencies | 8 lines | 1 line | 87% |
| Class with 5 methods | 25 lines | 7 lines | 72% |
| Function | 12 lines | 3 lines | 75% |
| Overall blueprint | ~60 lines | ~15 lines | 75% |

## Blueprint References

Blueprints can reference other blueprints for modular design:

### Reference Syntax
- `@module.name[Item1, Item2]` - Import specific items from a blueprint
- `@module.name` - Import entire blueprint module
- `@.relative` - Reference blueprint in same directory
- `@..parent` - Reference blueprint in parent directory

### Dependency Resolution
When generating code, the system:
1. Discovers all blueprint files in the project
2. Resolves references recursively
3. Includes referenced blueprints in the generation context
4. Handles circular dependencies automatically

### Benefits
- **Modular design** - Break complex systems into focused blueprints
- **Reusability** - Share common components across blueprints
- **Maintainability** - Change propagates through references
- **Context awareness** - LLM sees full system architecture

## Benefits

1. **75% smaller context** - More blueprints fit in LLM context window
2. **Faster to write** - Less boilerplate
3. **Easier to scan** - Key information is immediately visible
4. **Still clear for LLMs** - Maintains all necessary information
5. **Flexible** - Can add comments where needed
6. **Modular** - Reference other blueprints for complex systems

