"""Utility functions used throughout the blueprints package."""

import os
from pathlib import Path
from .constants import FALLBACK_BLUEPRINT_SPEC, get_api_key_error


def load_blueprint_spec() -> str:
    """Load blueprint specification from BLUEPRINTS_SPEC.md or return fallback."""
    spec_path = Path(__file__).parent.parent.parent / "BLUEPRINTS_SPEC.md"
    if spec_path.exists():
        return spec_path.read_text()
    return FALLBACK_BLUEPRINT_SPEC


def check_anthropic_api_key(purpose: str) -> None:
    """Check if ANTHROPIC_API_KEY is set, raise ValueError if not."""
    if not os.getenv('ANTHROPIC_API_KEY'):
        raise ValueError(get_api_key_error(purpose))


def safe_operation(operation, default_result=None, error_message=None):
    """Execute operation safely, returning default_result on any exception."""
    try:
        return operation()
    except Exception as e:
        if error_message:
            # Optionally log the error message if logging is configured
            pass
        return default_result