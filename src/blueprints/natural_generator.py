"""Enhanced code generator for natural language blueprints.

This module provides backward compatibility while using the new architecture.
"""

from pathlib import Path
from typing import Optional, Dict, List

from .parser import Blueprint
from .code_generator import NaturalCodeGenerator as CoreNaturalCodeGenerator
from .project_generator import ProjectGenerator


class NaturalCodeGenerator:
    """Enhanced code generator optimized for natural language blueprints.
    
    This class maintains backward compatibility while using the new architecture.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with focused modules."""
        self.core_generator = CoreNaturalCodeGenerator(api_key=api_key)
        self.project_generator = ProjectGenerator(self.core_generator)

    def _create_natural_blueprint_prompt(
        self,
        blueprint: Blueprint,
        language: str,
        context_parts: List[str],
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a prompt optimized for natural language blueprints."""
        return self.core_generator.prompt_builder.build_natural_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )

    def _format_natural_blueprint_imports(
        self, blueprint_refs: List[str], current_module: Optional[str] = None
    ) -> str:
        """Format natural blueprint dependency requirements for import instructions."""
        return self.core_generator.prompt_builder._format_natural_blueprint_imports(
            blueprint_refs, current_module
        )

    def generate_from_natural_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code directly from a natural language blueprint."""
        return self.core_generator.generate_natural_blueprint(
            blueprint, context_parts, language, dependency_versions
        )

    def generate_single_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Override to handle both natural and structured blueprints."""
        return self.core_generator.generate_single_blueprint(
            blueprint, context_parts, language, dependency_versions
        )

    # Backward compatibility properties
    @property
    def api_key(self):
        """Access to API key for backward compatibility."""
        return self.core_generator.api_key
    
    @property
    def client(self):
        """Access to Anthropic client for backward compatibility."""
        return self.core_generator.client
    
    @property
    def model(self):
        """Access to model for backward compatibility."""
        return self.core_generator.model
    
    @property
    def max_tokens(self):
        """Access to max_tokens for backward compatibility."""
        return self.core_generator.max_tokens
    
    @property
    def temperature(self):
        """Access to temperature for backward compatibility."""
        return self.core_generator.temperature
    
    def _extract_code_from_response(self, response: str) -> str:
        """Delegate to core generator for code extraction."""
        return self.core_generator._extract_code_from_response(response)


# Create a unified parser and generator that handles both formats
class UnifiedBlueprintSystem:
    """Unified system that handles both structured and natural language blueprints."""

    def __init__(self, api_key: Optional[str] = None):
        from .parser import BlueprintParser

        self.parser = BlueprintParser()
        self.generator = NaturalCodeGenerator(api_key=api_key)

    def parse_file(self, file_path: Path):
        """Parse a blueprint file of any supported format."""
        return self.parser.parse_file(file_path)

    def generate_code(
        self, blueprint, context_parts: List[str], language: str = "python", **kwargs
    ):
        """Generate code from any supported blueprint format."""
        return self.generator.generate_single_blueprint(
            blueprint, context_parts, language, **kwargs
        )
