"""Code generator module that uses Claude API to generate code from blueprints.

This module provides backward compatibility by delegating to the new focused modules.
"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple

from .parser import Blueprint
from .resolver import ResolvedBlueprint
from .code_generator import CodeGenerator as CoreCodeGenerator
from .project_generator import ProjectGenerator


class CodeGenerator:
    """Main code generator interface that delegates to focused modules.
    
    This class maintains backward compatibility while using the new architecture.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the code generator with focused modules."""
        self.core_generator = CoreCodeGenerator(api_key=api_key, model=model)
        self.project_generator = ProjectGenerator(self.core_generator)

    def _format_component_for_prompt(self, component):
        """Delegate to prompt builder for component formatting."""
        return self.core_generator.prompt_builder._format_component_for_prompt(component)

    def _extract_code_from_response(self, response: str) -> str:
        """Delegate to core generator for code extraction."""
        return self.core_generator._extract_code_from_response(response)

    def generate_project(
        self,
        resolved: ResolvedBlueprint,
        output_dir: Path,
        language: str = "python",
        force: bool = False,
        main_md_path: Optional[Path] = None,
        verify: bool = True,
    ) -> Dict[str, Path]:
        """Generate code for all blueprints in dependency order."""
        return self.project_generator.generate_project(
            resolved, output_dir, language, force, main_md_path, verify
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

    def generate_single_with_context(
        self,
        resolved: ResolvedBlueprint,
        output_path: Path,
        language: str = "python",
        force: bool = False,
        verify: bool = True,
    ) -> Path:
        """Generate a single file with all dependencies as context."""
        return self.project_generator.generate_single_with_context(
            resolved, output_path, language, force, verify
        )

    def _create_single_blueprint_prompt(
        self,
        blueprint: Blueprint,
        language: str,
        context_parts: List[str],
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a prompt for generating a single blueprint."""
        return self.core_generator.prompt_builder.build_single_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )

    def _extract_function_signatures(self, blueprint: Blueprint) -> str:
        """Extract function signatures from blueprint."""
        return self.core_generator.prompt_builder._extract_function_signatures(blueprint)

    def _format_blueprint_import_requirements(
        self, blueprint_refs: List, current_module: Optional[str] = None
    ) -> str:
        """Format blueprint dependency requirements."""
        return self.core_generator.prompt_builder._format_blueprint_imports(
            blueprint_refs, current_module
        )

    def _get_file_extension(self, language: str) -> str:
        """Get the appropriate file extension for the language."""
        return self.core_generator._get_file_extension(language)

    def _extract_dependency_versions(self, main_md_path: Path) -> Dict[str, str]:
        """Extract dependency names and versions from main.md."""
        return self.core_generator.extract_dependency_versions(main_md_path)

    def _create_python_init_files(
        self, generated_files: Dict[str, Path], force: bool = False
    ) -> Dict[str, Path]:
        """Create __init__.py files in all directories containing Python files."""
        return self.project_generator._create_python_init_files(generated_files, force)

    def _find_project_root(
        self, resolved: ResolvedBlueprint, main_md_path: Optional[Path] = None
    ) -> Path:
        """Find the project root directory by looking for main.md."""
        return self.project_generator._find_project_root(resolved, main_md_path)

    def _find_main_md_in_project(self, start_path: Path) -> Optional[Path]:
        """Find main.md by walking up the directory tree from start_path."""
        return self.core_generator.find_main_md_in_project(start_path)


    def generate_with_verification(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        max_retries: int = 3,
        project_root: Optional[Path] = None,
        main_md_path: Optional[Path] = None,
    ) -> Tuple[str, List]:
        """Generate code with verification and retry loop."""
        return self.core_generator.generate_with_verification(
            blueprint, context_parts, language, max_retries, project_root, main_md_path
        )

    def generate_single_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code for a single blueprint with context."""
        return self.core_generator.generate_single_blueprint(
            blueprint, context_parts, language, dependency_versions
        )
