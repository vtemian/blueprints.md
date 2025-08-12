"""Core code generation functionality using Claude API."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from anthropic import Anthropic

from .logging_config import get_logger
from .parser import Blueprint
from .resolver import ResolvedBlueprint, create_smart_resolver
from .adaptive_prompt_generator import AdaptivePromptBuilder
from .intelligent_context_curator import SmartContextBuilder
from .iterative_quality_improver import QualityEnhancedCodeGenerator
from .config import config as default_config
from .verifier import CodeVerifier


class CodeGenerator:
    """Core code generator that handles Claude API interactions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize with API key and model configuration."""
        logger = get_logger('generator')
        
        if Anthropic is None:
            raise ImportError("anthropic package is required for code generation. Install with: pip install anthropic")
            
        self.api_key = api_key or default_config.get_api_key()
        logger.debug(f"API key provided: {'Yes' if self.api_key else 'No'}")
        
        if not self.api_key:
            logger.error("No API key found in environment or parameters")
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        logger.debug("Initializing Anthropic client...")
        self.client = Anthropic(api_key=self.api_key)
        logger.debug("Anthropic client initialized successfully")
        self.model = model or default_config.default_model
        self.max_tokens = default_config.max_tokens
        self.temperature = default_config.temperature
        self.prompt_builder = AdaptivePromptBuilder()
        self.context_builder = SmartContextBuilder()

    def generate_single_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code for a single blueprint with context."""
        logger = get_logger('generator')
        logger.info(f"Generating {language} code for: {blueprint.module_name}")
        logger.debug(f"Context parts: {len(context_parts)}")
        if dependency_versions:
            logger.debug(f"Dependencies: {list(dependency_versions.keys())}")
        
        prompt = self.prompt_builder.build_single_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )
        return self._call_claude_api(prompt)

    def generate_natural_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code from a natural language blueprint."""
        logger = get_logger('generator')
        logger.info(f"Generating {language} code from natural blueprint: {blueprint.module_name}")
        logger.debug(f"Context parts: {len(context_parts)}")
        if dependency_versions:
            logger.debug(f"Dependencies: {list(dependency_versions.keys())}")
        
        prompt = self.prompt_builder.build_natural_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )
        return self._call_claude_api(prompt)

    def generate_with_verification(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        max_retries: int = 3,
        project_root: Optional[Path] = None,
        main_md_path: Optional[Path] = None,
    ) -> Tuple[str, List]:
        """Generate code with simple verification (no retries)."""

        if project_root is None and blueprint.file_path:
            project_root = blueprint.file_path.parent

        # Extract dependency versions if available
        dependency_versions = {}
        if main_md_path and main_md_path.exists():
            dependency_versions = self.extract_dependency_versions(main_md_path)

        # Generate code once
        code = self.generate_single_blueprint(
            blueprint, context_parts, language, dependency_versions
        )

        # Simple verification (caller handles retries if needed)
        verifier = CodeVerifier(project_root)
        results = verifier.verify_all(code, blueprint)

        # Record result for adaptive prompt learning
        success = all(result.success for result in results)
        verification_errors = [result.error_message for result in results if not result.success and result.error_message]
        self.prompt_builder.record_generation_result(blueprint, language, success, verification_errors)

        return code, results

    def create_blueprint_context(
        self,
        blueprint: Blueprint,
        resolved: ResolvedBlueprint,
        generated_context: Dict[str, str],
        language: str,
    ) -> List[str]:
        """Create intelligently curated context for blueprint generation."""
        return self.context_builder.create_blueprint_context(
            blueprint, resolved, generated_context, language
        )

    def create_comprehensive_context(self, resolved: ResolvedBlueprint, language: str) -> List[str]:
        """Create intelligently curated comprehensive context."""
        return self.context_builder.create_comprehensive_context(resolved, language)

    def extract_dependency_versions(self, main_md_path: Path) -> Dict[str, str]:
        """Extract dependency names and versions from main.md."""
        if not main_md_path or not main_md_path.exists():
            return {}

        dependency_versions = {}
        content = main_md_path.read_text()


        in_deps_section = False

        for line in content.splitlines():
            line = line.strip()

            # Check for dependency section headers
            if ("## Third-party Dependencies" in line or "## Dependencies" in line or
                "Dependencies:" in line or "Dependencies to Install:" in line):
                in_deps_section = True
                continue
            elif line.startswith("##") or (line.endswith(":") and not line.startswith("-")):
                in_deps_section = False
                continue

            # Parse dependency lines
            if in_deps_section and line.startswith("- "):
                version_match = re.match(r"- ([a-zA-Z0-9\-_\[\]]+)([><=~!]+)?([0-9.]+)?", line)
                if version_match and version_match.group(3):
                    name = version_match.group(1).split("[")[0]
                    version = version_match.group(3)
                    operator = version_match.group(2) if version_match.group(2) else ">="
                    dependency_versions[name] = f"{operator}{version}"
                else:
                    desc_match = re.match(r"- ([a-zA-Z0-9\-_\[\]]+)(\s*-.*)?", line)
                    if desc_match:
                        name = desc_match.group(1).split("[")[0]
                        dependency_versions[name] = "latest"

        return dependency_versions

    def find_main_md_in_project(self, start_path: Path) -> Optional[Path]:
        """Find main.md by walking up the directory tree from start_path."""
        current_path = start_path.resolve()

        while current_path != current_path.parent:
            main_md = current_path / "main.md"
            if main_md.exists():
                return main_md
            current_path = current_path.parent

        main_md = current_path / "main.md"
        if main_md.exists():
            return main_md

        return None

    def determine_output_path(self, blueprint: Blueprint, output_dir: Path, language: str) -> Path:
        """Determine the output file path for a blueprint."""
        if blueprint.file_path:
            blueprint_dir = blueprint.file_path.parent
            filename = f"{blueprint.file_path.stem}{self._get_file_extension(language)}"
            return blueprint_dir / filename

        module_parts = blueprint.module_name.split(".")
        filename = f"{module_parts[-1]}{self._get_file_extension(language)}"

        if len(module_parts) > 1:
            file_dir = output_dir / Path(*module_parts[:-1])
            file_dir.mkdir(parents=True, exist_ok=True)
            return file_dir / filename

        return output_dir / filename

    def save_generated_code(self, code: str, output_path: Path, force: bool) -> None:
        """Save generated code to file with force flag handling."""
        if output_path.exists() and not force:
            raise RuntimeError(
                f"File {output_path} already exists. Use --force to overwrite."
            )

        output_path.write_text(code)

    def _call_claude_api(self, prompt: str) -> str:
        """Make API call to Claude and extract clean code."""
        logger = get_logger('generator')
        
        # Validate API key is available
        if not self.api_key:
            logger.error("No API key available for Claude API call")
            raise RuntimeError("No API key provided for code generation")
        
        try:
            logger.debug(f"Making API call to {self.model} (prompt: {len(prompt)} chars)")
            logger.debug(f"Using API key: {'*' * (len(self.api_key) - 8) + self.api_key[-8:] if len(self.api_key) > 8 else '***'}")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            
            logger.debug(f"Received response ({len(response.content[0].text)} chars)")
            code = self._extract_code_from_response(response.content[0].text)
            logger.info(f"Successfully generated {len(code)} characters of code")
            return code
            
        except Exception as e:
            logger.error(f"API call failed: {type(e).__name__}: {str(e)}")
            if "api_key" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.error("This appears to be an API key issue. Please check your ANTHROPIC_API_KEY.")
            raise RuntimeError(f"Failed to generate code: {str(e)}")

    def _extract_code_from_response(self, response: str) -> str:
        """Extract clean code from Claude's response."""
        lines = response.strip().split("\n")

        if lines[0].startswith("```"):
            code_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```") and not in_code_block:
                    in_code_block = True
                    continue
                elif line.startswith("```") and in_code_block:
                    break
                elif in_code_block:
                    code_lines.append(line)
            return "\n".join(code_lines)

        return response.strip()

    def _get_file_extension(self, language: str) -> str:
        """Get the appropriate file extension for the language."""
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "cpp": ".cpp",
            "c": ".c",
        }
        return extensions.get(language.lower(), ".txt")


class NaturalCodeGenerator(CodeGenerator):
    """Enhanced code generator for natural language blueprints."""

    def generate_single_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Override to handle both natural and structured blueprints."""
        is_natural = bool(blueprint.requirements or blueprint.sections or blueprint.dependencies)
        
        if is_natural:
            return self.generate_natural_blueprint(
                blueprint, context_parts, language, dependency_versions
            )
        else:
            return super().generate_single_blueprint(
                blueprint, context_parts, language, dependency_versions
            )


