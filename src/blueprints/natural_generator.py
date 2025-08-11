"""Enhanced code generator for natural language blueprints."""

from pathlib import Path
from typing import Optional, Dict, List
from anthropic import Anthropic

from .natural_parser import NaturalBlueprint, BlueprintAdapter
from .generator import CodeGenerator
from .config import config as default_config


class NaturalCodeGenerator(CodeGenerator):
    """Enhanced code generator optimized for natural language blueprints."""

    def _create_natural_blueprint_prompt(
        self,
        blueprint: NaturalBlueprint,
        language: str,
        context_parts: List[str],
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a prompt optimized for natural language blueprints."""
        prompt_parts = context_parts.copy()

        prompt_parts.extend(
            [
                f"Module: {blueprint.module_name}",
                f"Description: {blueprint.description}",
                "",
            ]
        )

        # Add dependencies if present
        if blueprint.dependencies:
            prompt_parts.extend(
                ["Dependencies:", *[f"- {dep}" for dep in blueprint.dependencies], ""]
            )

        # Add dependency version information if available
        if dependency_versions:
            prompt_parts.extend(
                [
                    "Third-party dependency versions to target:",
                    *[
                        f"- {name}: {version}"
                        for name, version in dependency_versions.items()
                    ],
                    "",
                ]
            )

        # Add requirements
        if blueprint.requirements:
            prompt_parts.extend(
                ["Requirements:", *[f"- {req}" for req in blueprint.requirements], ""]
            )

        # Add all other sections
        for section_name, content in blueprint.sections.items():
            if section_name not in ["dependencies", "requirements"]:
                prompt_parts.extend(
                    [
                        f"{section_name.title()}:",
                        *[
                            f"- {item}" if not item.startswith("-") else item
                            for item in content
                        ],
                        "",
                    ]
                )

        # Add blueprint dependency import requirements if present
        blueprint_import_requirements = ""
        if blueprint.blueprint_refs:
            blueprint_import_requirements = self._format_natural_blueprint_imports(
                blueprint.blueprint_refs, blueprint.module_name
            )

        prompt_parts.extend(
            [
                "",
                f"Generate complete {language} code with:",
                "1. Automatically infer and add all necessary imports (standard library, third-party, and local)",
                "2. Full implementation following the requirements and descriptions above",
                "3. Type hints and concise docstrings",
                "4. Error handling where appropriate",
                "5. Follow best practices for the target language",
                "6. Use LATEST API patterns and avoid deprecated features",
                "",
                "Import Requirements:",
                "- Import only what you actually use in the code",
                "- Use standard library imports when possible",
                "- Infer third-party packages from the descriptions and functionality",
                "- Group imports: standard library, third-party, then local imports",
                "- Use ABSOLUTE imports only (no relative imports)",
                "- Add all necessary third-party imports for functionality described:",
                "  * For SQLAlchemy: create_engine, sessionmaker, declarative_base, Session, Column, etc.",
                "  * For FastAPI: FastAPI, APIRouter, Depends, HTTPException, status, etc.",
                "  * For Pydantic: BaseModel, Field, etc.",
                blueprint_import_requirements,
                "",
                "Modern API Guidelines:",
                "- For FastAPI: Use lifespan context managers instead of @app.on_event decorators",
                "- For SQLAlchemy 2.0+: Use modern declarative_base patterns",
                "- For Pydantic 2.0+: Use model_config instead of Config class",
                "- Always prefer the latest stable API patterns over deprecated ones",
                "",
                "Code Quality Guidelines:",
                "- Write clean, readable code with clear variable names",
                "- Keep functions focused and reasonably sized (max 30-50 lines)",
                "- Use appropriate error handling and validation",
                "- Follow the language's naming conventions and best practices",
                "- Add helpful comments for complex logic",
                "",
                "Implementation Approach:",
                "- Read the requirements carefully and implement ALL specified functionality",
                "- Use the description to understand the context and purpose", 
                "- Pay attention to business rules and constraints in additional sections",
                "- If dependencies are listed (like uvicorn, fastapi, etc.), ACTUALLY USE THEM in the implementation",
                "- If the blueprint mentions server setup, configuration, or startup - IMPLEMENT the actual code for it",
                "- Don't just log messages - implement the real functionality described",
                "- Ensure the implementation is production-ready and robust",
                "",
                "Return ONLY the code without explanations, comments, or tests.",
            ]
        )

        return "\n".join(prompt_parts)

    def _format_natural_blueprint_imports(
        self, blueprint_refs: List[str], current_module: Optional[str] = None
    ) -> str:
        """Format natural blueprint dependency requirements for import instructions."""
        if not blueprint_refs:
            return ""

        lines = ["", "BLUEPRINT DEPENDENCY REQUIREMENTS:"]
        for ref in blueprint_refs:
            # Clean up the reference
            clean_ref = ref.lstrip("@").lstrip("./")
            if clean_ref.startswith("../"):
                clean_ref = clean_ref[3:]  # Remove ../

            # Convert to import instruction
            lines.append(
                f"- {ref} → Analyze this blueprint and import the necessary components"
            )

        return "\n".join(lines)

    def generate_from_natural_blueprint(
        self,
        blueprint: NaturalBlueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code directly from a natural language blueprint."""
        prompt = self._create_natural_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            return self._extract_code_from_response(response.content[0].text)

        except Exception as e:
            raise RuntimeError(f"Failed to generate code: {str(e)}")

    def generate_single_blueprint(
        self,
        blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Override to handle both natural and structured blueprints."""
        # Check if this is a natural blueprint (wrapped in adapter)
        if isinstance(blueprint, BlueprintAdapter):
            return self.generate_from_natural_blueprint(
                blueprint.natural, context_parts, language, dependency_versions
            )
        else:
            # Fall back to the original method for structured blueprints
            return super().generate_single_blueprint(
                blueprint, context_parts, language, dependency_versions
            )


# Create a unified parser and generator that handles both formats
class UnifiedBlueprintSystem:
    """Unified system that handles both structured and natural language blueprints."""

    def __init__(self, api_key: Optional[str] = None):
        from .natural_parser import HybridBlueprintParser

        self.parser = HybridBlueprintParser()
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
