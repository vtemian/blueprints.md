"""Constants used throughout the blueprints package."""

# Claude API Configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 4000

# Error Messages
API_KEY_ERROR_TEMPLATE = (
    "ANTHROPIC_API_KEY environment variable is required for {purpose}. "
    "Set it with: export ANTHROPIC_API_KEY=your_key_here"
)

def get_api_key_error(purpose: str) -> str:
    """Generate standardized API key error message."""
    return API_KEY_ERROR_TEMPLATE.format(purpose=purpose)

# Blueprint Specification
FALLBACK_BLUEPRINT_SPEC = """
Blueprint files use natural language format:
- Start with # [module.name]  
- Description of what the module does
- Dependencies: [list of dependencies and @blueprint/references]
- Requirements: [list of requirements]
- Additional sections as needed
"""