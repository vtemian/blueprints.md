# Blueprint Specification

Natural language format for describing code modules that LLMs can understand and implement.

## Format

```markdown
# [module.name]

[Brief description of what this module does]

Dependencies: [libraries, @blueprint/references]

Requirements:
- [requirement 1]
- [requirement 2]

[Additional sections as needed]
```

## Blueprint References

Reference other blueprints using `@` prefix:
- `@../models/user` - Blueprint in parent directory
- `@./services/auth` - Blueprint in current directory
- `@components/button` - Absolute reference from project root

## Examples

### Simple Model
```markdown
# models.user

User model for authentication.

Dependencies: sqlalchemy, bcrypt

Requirements:
- User table with id, email, password_hash, created_at
- Password hashing and verification methods  
- Email uniqueness validation
```

### API Endpoints
```markdown
# api.products

Product management endpoints.

Dependencies: fastapi, @../models/product

Requirements:
- GET /products with search and pagination
- POST/PUT/DELETE for admin product management
- Include product images and categories
```

### Background Service
```markdown
# jobs.email_worker

Email sending background worker.

Dependencies: celery, redis, @../services/email

Requirements:
- Process email jobs asynchronously
- Retry failed emails with exponential backoff
- Support different email types (welcome, notifications)
- Log all email attempts
```

## Best Practices

- **Be concise**: Include only essential information
- **List dependencies**: External libraries and blueprint references
- **Focus on requirements**: What the module must do
- **Add context when needed**: Business rules or constraints