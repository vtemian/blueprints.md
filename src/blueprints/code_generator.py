"""Core code generation functionality using Claude API."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .parser import Blueprint
from .resolver import BlueprintResolver, ResolvedBlueprint
from .prompt_builder import PromptBuilder
from .config import config as default_config

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


class CodeGenerator:
    """Core code generator that handles Claude API interactions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize with API key and model configuration."""
        if Anthropic is None:
            raise ImportError("anthropic package is required for code generation. Install with: pip install anthropic")
            
        self.api_key = api_key or default_config.get_api_key()
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model or default_config.default_model
        self.max_tokens = default_config.max_tokens
        self.temperature = default_config.temperature
        self.prompt_builder = PromptBuilder()

    def generate_single_blueprint(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code for a single blueprint with context."""
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
        """Generate code with verification and retry loop."""
        from .verifier import GenerationVerifier

        if project_root is None and blueprint.file_path:
            project_root = blueprint.file_path.parent

        verifier = GenerationVerifier(
            max_retries=max_retries, language=language, project_root=project_root
        )
        return verifier.verify_and_improve(
            self, blueprint, context_parts, language, main_md_path
        )

    def create_blueprint_context(
        self,
        blueprint: Blueprint,
        resolved: ResolvedBlueprint,
        generated_context: Dict[str, str],
        language: str,
    ) -> List[str]:
        """Create context for blueprint generation including dependencies."""
        resolver = BlueprintResolver()
        dependencies = resolver.get_dependencies_for_blueprint(blueprint, resolved)

        if not dependencies:
            return [f"Generate {language} code from this blueprint:", ""]

        context_parts = ["You have access to the following dependency modules:", ""]

        for dep in dependencies:
            if dep.module_name in generated_context:
                context_parts.extend([
                    f"=== Module: {dep.module_name} ===",
                    "Blueprint:",
                    dep.raw_content.strip(),
                    "",
                    "Generated code:",
                    generated_context[dep.module_name],
                    "",
                ])

        context_parts.extend([
            "=== END OF DEPENDENCIES ===",
            "",
            f"Now generate {language} code for the following blueprint:",
            "",
        ])

        return context_parts

    def create_comprehensive_context(self, resolved: ResolvedBlueprint, language: str) -> List[str]:
        """Create comprehensive context with all dependencies as context."""
        context_parts = []

        if resolved.dependencies:
            context_parts.extend([
                "You have access to the following blueprint dependencies:",
                "",
            ])

            for dep in resolved.dependencies:
                context_parts.extend([
                    f"=== Blueprint: {dep.module_name} ===",
                    dep.raw_content.strip(),
                    "",
                ])

            context_parts.extend([
                "=== END OF DEPENDENCIES ===",
                "",
                f"Now generate {language} code for the following blueprint, using the above blueprints as context:",
                "",
            ])
        else:
            context_parts.extend([f"Generate {language} code from this blueprint:", ""])

        return context_parts

    def extract_dependency_versions(self, main_md_path: Path) -> Dict[str, str]:
        """Extract dependency names and versions from main.md."""
        if not main_md_path or not main_md_path.exists():
            return {}

        dependency_versions = {}
        content = main_md_path.read_text()

        import re

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