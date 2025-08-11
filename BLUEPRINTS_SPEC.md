# Blueprint Specification

A natural, prompt-like format for describing code modules that LLMs can easily understand and implement.

## Philosophy

Instead of rigid syntax rules, blueprints are written as **conversational prompts** that describe what you want built. This approach is:

- **Natural**: Write like you're explaining to a developer
- **Flexible**: Adapt the format to your needs
- **Intuitive**: No syntax to memorize
- **Powerful**: Include context, constraints, and reasoning

## Basic Format

```markdown
# [module.name]

[Natural description of what this module should do]

Dependencies: [blueprint references and external libraries as needed]

Requirements:
- [key requirement 1]  
- [key requirement 2]
- [implementation detail or constraint]

Additional Notes:
- [performance considerations]
- [security requirements]  
- [business rules or context]
```

## Key Principles

### 1. Write Conversationally
Describe what you want as if explaining to a colleague:

```markdown
# services.payment

Create a payment processing service that handles credit card transactions.

Dependencies: stripe, @../models/order

Requirements:
- Integrate with Stripe API for payment processing
- Support one-time payments and subscriptions  
- Handle payment failures gracefully with retry logic
- Store payment records for audit trails
- Send confirmation emails after successful payments

Additional Notes:
- Use Stripe webhooks for real-time status updates
- Implement idempotency keys to prevent duplicate charges
- Add comprehensive logging for debugging payment issues
```

### 2. Focus on Intent, Not Implementation
Describe **what** you want, not exactly **how** to build it:

❌ **Too Implementation-Focused:**
```markdown
PaymentService:
  - __init__(api_key: str, webhook_secret: str)
  - process_payment(amount: int, currency: str, card_token: str) -> PaymentResult
  - handle_webhook(payload: str, signature: str) -> None
```

✅ **Intent-Focused:**
```markdown
Build a PaymentService that can process credit card payments securely, handle webhook notifications from Stripe, and manage payment state transitions.
```

### 3. Include Context and Constraints
Help the LLM understand the bigger picture:

```markdown
# api.auth

Build authentication endpoints for a multi-tenant SaaS application.

Dependencies: fastapi, jwt, @../models/user, @../models/tenant

Requirements:
- Support email/password and OAuth2 (Google, GitHub) login
- Generate JWT tokens with tenant context
- Implement role-based permissions (admin, user, viewer)
- Rate limit login attempts to prevent brute force attacks
- Support password reset via email

Business Context:
- Users belong to tenants and can only access their tenant's data
- Some users can belong to multiple tenants
- Admin users can invite others to their tenant
- Free tier has max 5 users per tenant, paid tiers are unlimited

Security Notes:
- Hash passwords with bcrypt
- Use secure session cookies in production
- Implement CSRF protection
- Log all authentication events for security auditing
```

## Blueprint References

Reference other blueprints using the `@` prefix for modular design:

### Reference Syntax
- `@../models/user` - Blueprint in parent directory's models folder
- `@./services/auth` - Blueprint in current directory's services folder  
- `@components/button` - Absolute reference from project root

### Dependency Examples
```markdown
Dependencies: fastapi, sqlalchemy, @../models/user, @./services/email
```

When generating code, the system automatically:
1. Discovers referenced blueprints
2. Includes them in the generation context
3. Handles circular dependencies
4. Resolves import paths correctly

## Complete Examples

### Example 1: Simple Data Model
```markdown
# models.user

Create a User model for authentication and user management.

Dependencies: sqlalchemy, @./base

Requirements:
- User table with id, email, username, password_hash, created_at fields
- Email must be unique and validated
- Include methods for password hashing and verification
- Add relationship to other models like posts or orders
- Support soft deletion (is_active field)

Additional Notes:
- Hash passwords with bcrypt before storing
- Add indexes on email and username for fast lookups
- Include created_at and updated_at timestamps
```

### Example 2: API Endpoints
```markdown
# api.products

Build product management API endpoints for an e-commerce platform.

Dependencies: fastapi, @../models/product, @../models/category, @../services/auth

Requirements:
- GET /products with search, filtering, and pagination
- GET /products/{id} for detailed product view
- POST, PUT, DELETE endpoints for admin-only product management
- Support product images, categories, and inventory tracking
- Include featured products and related products endpoints

Business Rules:
- Only active products shown to regular users
- Admins can manage all products regardless of status
- Products must belong to a valid category
- Price changes should log audit trail
- Out-of-stock products still visible but marked

Performance Notes:
- Cache popular product searches
- Optimize database queries with proper joins
- Implement pagination to handle large product catalogs
```

### Example 3: Background Service
```markdown
# jobs.email_worker

Create a background worker for processing email sending jobs.

Dependencies: celery, redis, @../services/email, @../models/email_log

Requirements:
- Process email sending jobs asynchronously
- Support different email types (welcome, notifications, marketing)
- Handle email delivery failures with retry logic
- Log all email attempts and results
- Support email templates with dynamic content

Configuration:
- Use Redis as message broker
- Retry failed emails up to 3 times with exponential backoff
- Process emails in batches to avoid rate limits
- Dead letter queue for permanently failed emails

Monitoring:
- Track email delivery rates and failures
- Alert on high failure rates
- Provide metrics for email volume and processing times
```

## Migration Guide

### Converting Existing Blueprints

**Old Structured Format:**
```markdown
# api.auth
Authentication endpoints

deps: @..models.user[User]; @..services.auth[AuthService]

@router.post("/login")
async login(credentials: LoginRequest) -> TokenResponse:
  # Authenticate user and return JWT token
```

**New Prompt Format:**
```markdown
# api.auth

Build authentication endpoints for user login and registration.

Dependencies: fastapi, @../models/user, @../services/auth

Requirements:
- POST /login endpoint that accepts email/password and returns JWT token
- POST /register for new user registration with email verification
- POST /logout to invalidate user sessions
- Include proper error handling and validation

Security:
- Rate limit login attempts
- Use secure password hashing
- Implement CSRF protection for web clients
```

## Benefits

1. **Easier to Write**: No syntax to memorize - just describe what you want
2. **More Flexible**: Adapt the format to each module's needs
3. **Better Context**: Include business rules, constraints, and reasoning
4. **Natural Language**: Write like you're talking to a developer
5. **LLM-Friendly**: Models excel at understanding natural language instructions
6. **Maintainable**: Changes to requirements are easy to express and understand

## Best Practices

- **Be Specific**: Include important details about behavior and constraints
- **Provide Context**: Explain the business purpose and how the module fits
- **List Dependencies**: Mention external libraries and blueprint references
- **Include Examples**: Show expected inputs/outputs when helpful
- **Consider Edge Cases**: Mention error handling and validation requirements
- **Think Performance**: Note any scalability or efficiency concerns