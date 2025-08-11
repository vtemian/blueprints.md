"""Code generator module that uses Claude API to generate code from blueprints."""

import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from anthropic import Anthropic
from .parser import Blueprint, Component
from .resolver import BlueprintResolver, ResolvedBlueprint
from .config import config as default_config


class CodeGenerator:
    """Generates source code from blueprints using Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the code generator with an API key."""
        self.api_key = api_key or default_config.get_api_key()
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model or default_config.default_model
        self.max_tokens = default_config.max_tokens
        self.temperature = default_config.temperature

    def _format_component_for_prompt(self, component: Component) -> list:
        """Format a component for inclusion in the prompt."""
        parts = [""]

        if component.type == "class":
            header = f"Class {component.name}"
            if component.base_class:
                header += f"({component.base_class})"
            parts.append(header + ":")

            # Add methods
            for method in component.methods:
                method_str = f"  - {method.name}"
                if method.params:
                    method_str += f"({method.params})"
                else:
                    method_str += "()"
                if method.return_type:
                    method_str += f" -> {method.return_type}"
                if method.comment:
                    method_str += f"  # {method.comment}"
                if method.decorators:
                    for decorator in method.decorators:
                        parts.append(f"  {decorator}")
                parts.append(method_str)

        elif component.type == "function":
            if component.methods:  # Functions stored as single method
                method = component.methods[0]
                func_str = f"Function {method.name}({method.params})"
                if method.return_type:
                    func_str += f" -> {method.return_type}"
                parts.append(func_str)
                if component.docstring:
                    parts.append(f'  """{component.docstring}"""')

        elif component.type == "constant":
            const_str = f"Constant {component.name}"
            if "type" in component.properties:
                const_str += f": {component.properties['type']}"
            if component.value:
                const_str += f" = {component.value}"
            parts.append(const_str)

        elif component.type == "type_alias":
            parts.append(f"Type alias: {component.name} = {component.value}")

        return parts

    def _extract_code_from_response(self, response: str) -> str:
        """Extract clean code from Claude's response."""
        # Remove any markdown code blocks if present
        lines = response.strip().split("\n")

        # Check if response is wrapped in code blocks
        if lines[0].startswith("```"):
            # Find the closing code block
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

        # If no code blocks, return as is
        return response.strip()

    def generate_project(
        self,
        resolved: ResolvedBlueprint,
        output_dir: Path,
        language: str = "python",
        force: bool = False,
        main_md_path: Optional[Path] = None,
        verify: bool = True,
    ) -> Dict[str, Path]:
        """Generate code for all blueprints in dependency order with separate API calls."""
        output_dir.mkdir(parents=True, exist_ok=True)

        dependency_versions = self._extract_dependency_versions_safe(main_md_path)
        generated_files = {}
        generated_context = {}

        for blueprint in resolved.generation_order:
            try:
                code, output_path = self._generate_single_blueprint_file(
                    blueprint,
                    resolved,
                    dependency_versions,
                    language,
                    output_dir,
                    force,
                    verify,
                    main_md_path,
                    generated_context,
                )
                generated_files[blueprint.module_name] = output_path
                generated_context[blueprint.module_name] = code
            except Exception as e:
                raise RuntimeError(
                    f"Failed to generate code for {blueprint.module_name}: {str(e)}"
                )

        # Create Python package structure if needed
        if language.lower() == "python":
            init_files = self._create_python_init_files(generated_files, force)
            generated_files.update(init_files)

        # Generate Makefile
        makefile_path = self._generate_project_makefile(
            resolved, main_md_path, language, force
        )
        if makefile_path:
            generated_files["Makefile"] = makefile_path

        return generated_files

    def _extract_dependency_versions_safe(
        self, main_md_path: Optional[Path]
    ) -> Dict[str, str]:
        """Safely extract dependency versions from main.md."""
        if not main_md_path or not main_md_path.exists():
            return {}
        return self._extract_dependency_versions(main_md_path)

    def _generate_single_blueprint_file(
        self,
        blueprint: "Blueprint",
        resolved: ResolvedBlueprint,
        dependency_versions: Dict[str, str],
        language: str,
        output_dir: Path,
        force: bool,
        verify: bool,
        main_md_path: Optional[Path],
        generated_context: Dict[str, str],
    ) -> tuple[str, Path]:
        """Generate code for a single blueprint and return code and output path."""
        context_parts = self._create_blueprint_context(
            blueprint, resolved, generated_context, language
        )
        prompt = self._create_single_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )

        code = self._generate_code_with_verification(
            blueprint, context_parts, language, verify, main_md_path
        )

        output_path = self._determine_output_path(blueprint, output_dir, language)
        self._save_generated_code(code, output_path, force)

        return code, output_path

    def _create_blueprint_context(
        self,
        blueprint: "Blueprint",
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
                context_parts.extend(
                    [
                        f"=== Module: {dep.module_name} ===",
                        "Blueprint:",
                        dep.raw_content.strip(),
                        "",
                        "Generated code:",
                        generated_context[dep.module_name],
                        "",
                    ]
                )

        context_parts.extend(
            [
                "=== END OF DEPENDENCIES ===",
                "",
                f"Now generate {language} code for the following blueprint:",
                "",
            ]
        )

        return context_parts

    def _generate_code_with_verification(
        self,
        blueprint: "Blueprint",
        context_parts: List[str],
        language: str,
        verify: bool,
        main_md_path: Optional[Path],
    ) -> str:
        """Generate code for blueprint with optional verification."""
        if not verify:
            return self.generate_single_blueprint(blueprint, context_parts, language)

        project_root = blueprint.file_path.parent if blueprint.file_path else Path.cwd()
        code, verification_results = self.generate_with_verification(
            blueprint,
            context_parts,
            language,
            max_retries=2,
            project_root=project_root,
            main_md_path=main_md_path,
        )

        self._log_verification_warnings(blueprint.module_name, verification_results)
        return code

    def _log_verification_warnings(
        self, module_name: str, verification_results: List["VerificationResult"]
    ) -> None:
        """Log any verification warnings."""
        failed_verifications = [r for r in verification_results if not r.success]
        if failed_verifications:
            print(f"Warning: Blueprint {module_name} has verification issues:")
            for result in failed_verifications:
                print(f"  - {result.error_type}: {result.error_message}")

    def _determine_output_path(
        self, blueprint: "Blueprint", output_dir: Path, language: str
    ) -> Path:
        """Determine the output file path for a blueprint."""
        if blueprint.file_path:
            blueprint_dir = blueprint.file_path.parent
            filename = f"{blueprint.file_path.stem}{self._get_file_extension(language)}"
            return blueprint_dir / filename

        # Fallback to output_dir structure
        module_parts = blueprint.module_name.split(".")
        filename = f"{module_parts[-1]}{self._get_file_extension(language)}"

        if len(module_parts) > 1:
            file_dir = output_dir / Path(*module_parts[:-1])
            file_dir.mkdir(parents=True, exist_ok=True)
            return file_dir / filename

        return output_dir / filename

    def _save_generated_code(self, code: str, output_path: Path, force: bool) -> None:
        """Save generated code to file with force flag handling."""
        if output_path.exists() and not force:
            raise RuntimeError(
                f"File {output_path} already exists. Use --force to overwrite."
            )

        output_path.write_text(code)

    def _generate_project_makefile(
        self,
        resolved: ResolvedBlueprint,
        main_md_path: Optional[Path],
        language: str,
        force: bool,
    ) -> Optional[Path]:
        """Generate project Makefile."""
        project_root = self._find_project_root(resolved, main_md_path)
        return self._generate_makefile(
            resolved, project_root, language, force, main_md_path
        )

    def generate_single_with_context(
        self,
        resolved: ResolvedBlueprint,
        output_path: Path,
        language: str = "python",
        force: bool = False,
        verify: bool = True,
    ) -> Path:
        """Generate a single file with all dependencies as context in one API call."""
        # Create comprehensive context with all dependencies
        context_parts = []

        if resolved.dependencies:
            context_parts.extend(
                ["You have access to the following blueprint dependencies:", ""]
            )

            for dep in resolved.dependencies:
                context_parts.extend(
                    [
                        f"=== Blueprint: {dep.module_name} ===",
                        dep.raw_content.strip(),
                        "",
                    ]
                )

            context_parts.extend(
                [
                    "=== END OF DEPENDENCIES ===",
                    "",
                    f"Now generate {language} code for the following blueprint, using the above blueprints as context:",
                    "",
                ]
            )
        else:
            context_parts.extend([f"Generate {language} code from this blueprint:", ""])

        # Extract dependency versions if available
        dependency_versions = {}
        if resolved.main.file_path:
            project_root = resolved.main.file_path.parent
            main_md_path = self._find_main_md_in_project(project_root)
            if main_md_path:
                dependency_versions = self._extract_dependency_versions(main_md_path)

        # Create prompt for the main blueprint
        prompt = self._create_single_blueprint_prompt(
            resolved.main, language, context_parts, dependency_versions
        )

        # Generate code with full context and optional verification
        try:
            if verify:
                # Use verification loop for better code quality
                project_root = (
                    resolved.main.file_path.parent
                    if resolved.main.file_path
                    else output_path.parent
                )
                # Find main.md by walking up the directory tree
                main_md_for_verification = self._find_main_md_in_project(project_root)

                code, verification_results = self.generate_with_verification(
                    resolved.main,
                    context_parts,
                    language,
                    max_retries=2,
                    project_root=project_root,
                    main_md_path=main_md_for_verification,
                )
                # Log verification results if needed
                failed_verifications = [
                    r for r in verification_results if not r.success
                ]
                if failed_verifications:
                    print(
                        f"Warning: Blueprint {resolved.main.module_name} has verification issues:"
                    )
                    for result in failed_verifications:
                        print(f"  - {result.error_type}: {result.error_message}")
            else:
                # Direct generation without verification
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )

                code = self._extract_code_from_response(response.content[0].text)

            # Check if file exists and force flag
            if output_path.exists() and not force:
                import click

                if not click.confirm(f"File {output_path} already exists. Overwrite?"):
                    raise RuntimeError("Generation cancelled by user")

            # Save the code
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(code)

            return output_path

        except Exception as e:
            raise RuntimeError(
                f"Failed to generate code for {resolved.main.module_name}: {str(e)}"
            )

    def _create_single_blueprint_prompt(
        self,
        blueprint: Blueprint,
        language: str,
        context_parts: List[str],
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a prompt for generating a single blueprint."""
        prompt_parts = context_parts.copy()

        prompt_parts.extend(
            [
                f"Module: {blueprint.module_name}",
                f"Description: {blueprint.description}",
                "",
            ]
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

        # Format components
        if blueprint.components:
            prompt_parts.append("Components to implement:")
            for component in blueprint.components:
                prompt_parts.extend(self._format_component_for_prompt(component))

        # Add notes
        if blueprint.notes:
            prompt_parts.extend(
                [
                    "",
                    "Implementation notes:",
                    *[f"- {note}" for note in blueprint.notes],
                ]
            )

        # Add blueprint dependency import requirements if present
        blueprint_import_requirements = ""
        if blueprint.blueprint_refs:
            blueprint_import_requirements = self._format_blueprint_import_requirements(
                blueprint.blueprint_refs, blueprint.module_name
            )

        # Extract function signatures from blueprint to help with async/await decisions
        function_signatures = self._extract_function_signatures(blueprint)

        prompt_parts.extend(
            [
                "",
                f"Generate complete {language} code with:",
                "1. Automatically infer and add all necessary imports (standard library, third-party, and local)",
                "2. Full implementation of all components",
                "3. Type hints and concise docstrings",
                "4. Error handling where appropriate",
                "5. Follow the implementation notes",
                "6. Use LATEST API patterns and avoid deprecated features",
                "",
                "Import Requirements:",
                "- Import only what you actually use in the code",
                "- Use standard library imports when possible",
                "- Infer third-party packages from the component descriptions and functionality",
                "- Group imports: standard library, third-party, then local imports",
                "- Use ABSOLUTE imports only (no relative imports like 'from .module import')",
                "- CRITICAL: Add all necessary third-party imports for functions used in the code:",
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
                "- Avoid nested try/catch blocks - use early returns and guard clauses instead",
                "- Keep functions focused on a single responsibility (max 30 lines)",
                "- Use clear, descriptive variable names",
                "- Avoid high cognitive complexity - max 3 levels of nesting",
                "",
                "Async/Await Guidelines:",
                "- CRITICAL: Only use 'await' with async functions",
                "- Check function signatures before using await",
                "- If a function from another module is not async, do NOT await it",
                "- Common sync functions that should NOT be awaited:",
                "  * Most initialization functions unless explicitly async",
                "  * Functions from blueprints without 'async' prefix (e.g., init_db() -> None is SYNC)",
                "- When in doubt, check the blueprint signature - no 'async' means it's synchronous",
                "- Extract complex logic into well-named helper functions",
                "",
                function_signatures,
                "",
                "Return ONLY the code without explanations or tests.",
            ]
        )

        return "\n".join(prompt_parts)

    def _extract_function_signatures(self, blueprint: Blueprint) -> str:
        """Extract function signatures from blueprint to clarify async/sync nature."""
        if not blueprint.components:
            return ""

        signatures = [
            "Function signatures from blueprint (all are SYNC unless marked otherwise):"
        ]
        for component in blueprint.components:
            if component.type == "function":
                # In blueprints, functions are represented as components with methods
                # Extract the first method which represents the function itself
                if component.methods:
                    method = component.methods[0]
                    sig = f"- {method.name}("
                    if method.params:
                        sig += method.params
                    sig += ")"
                    if method.return_type:
                        sig += f" -> {method.return_type}"
                    # Check if marked as async
                    if method.is_async:
                        sig += " # ASYNC function - use await when calling"
                    else:
                        sig += " # SYNC function - do NOT use await when calling"
                    signatures.append(sig)

        # Also add info about imported functions from dependencies
        if blueprint.blueprint_refs:
            signatures.append("\nImported functions from dependencies:")
            for ref in blueprint.blueprint_refs:
                for item in ref.items:
                    if " as " in item:
                        parts = item.split(" as ")
                        if len(parts) == 2:
                            orig_name, alias = parts
                            signatures.append(
                                f"- {alias.strip()} (from {ref.module_path}) # Check source module to determine if async"
                            )
                        else:
                            signatures.append(
                                f"- {item.strip()} (from {ref.module_path}) # Check source module to determine if async"
                            )
                    else:
                        signatures.append(
                            f"- {item.strip()} (from {ref.module_path}) # Check source module to determine if async"
                        )

        return "\n".join(signatures) if len(signatures) > 1 else ""

    def _format_blueprint_import_requirements(
        self,
        blueprint_refs: List["BlueprintReference"],
        current_module: Optional[str] = None,
    ) -> str:
        """Format blueprint dependency requirements for import instructions."""
        if not blueprint_refs:
            return ""

        lines = ["", "BLUEPRINT DEPENDENCY REQUIREMENTS - MUST MATCH EXACTLY:"]
        for ref in blueprint_refs:
            # Handle both @.module and .module formats (parser may strip @)
            module_path = ref.module_path
            if module_path.startswith(".."):
                # Remove double dots for absolute import (from parent directory)
                module_path = module_path[2:]
            elif module_path.startswith("."):
                # Single dot - sibling module in same namespace
                if current_module and "." in current_module:
                    # Get parent namespace and append the sibling module
                    parent_namespace = ".".join(current_module.split(".")[:-1])
                    sibling_module = module_path[1:]  # Remove the dot
                    module_path = f"{parent_namespace}.{sibling_module}"
                else:
                    # Remove leading dot for absolute import (fallback)
                    module_path = module_path[1:]

            for item in ref.items:
                if " as " in item:
                    orig_item, alias = item.split(" as ")
                    expected_import = f"from {module_path} import {orig_item.strip()} as {alias.strip()}"
                    lines.append(f"- {ref.module_path}[{item}] → {expected_import}")
                else:
                    expected_import = f"from {module_path} import {item.strip()}"
                    lines.append(f"- {ref.module_path}[{item}] → {expected_import}")

        return "\n".join(lines)

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

    def _extract_dependency_versions(self, main_md_path: Path) -> Dict[str, str]:
        """Extract dependency names and versions from main.md."""
        dependency_versions = {}
        content = main_md_path.read_text()

        import re

        in_deps_section = False

        for line in content.splitlines():
            line = line.strip()

            # Check for dependency section headers (both old and new formats)
            if ("## Third-party Dependencies" in line or "## Dependencies" in line or
                "Dependencies:" in line or "Dependencies to Install:" in line):
                in_deps_section = True
                continue
            elif line.startswith("##") or (line.endswith(":") and not line.startswith("-")):
                in_deps_section = False
                continue

            # Parse dependency lines
            if in_deps_section and line.startswith("- "):
                # Handle both formats:
                # Old: - fastapi>=0.104.0
                # New: - fastapi - Web framework
                
                # First try the version format
                version_match = re.match(r"- ([a-zA-Z0-9\-_\[\]]+)([><=~!]+)?([0-9.]+)?", line)
                if version_match and version_match.group(3):  # Has version
                    name = version_match.group(1).split("[")[0]  # Remove extras like [standard]
                    version = version_match.group(3)
                    operator = version_match.group(2) if version_match.group(2) else ">="
                    dependency_versions[name] = f"{operator}{version}"
                else:
                    # Try new format: - package_name - description
                    desc_match = re.match(r"- ([a-zA-Z0-9\-_\[\]]+)(\s*-.*)?", line)
                    if desc_match:
                        name = desc_match.group(1).split("[")[0]  # Remove extras like [standard]
                        dependency_versions[name] = "latest"

        return dependency_versions

    def _create_python_init_files(
        self, generated_files: Dict[str, Path], force: bool = False
    ) -> Dict[str, Path]:
        """Create __init__.py files in all directories containing Python files."""
        init_files = {}

        # Collect all unique directories that contain Python files
        python_dirs = set()
        for module_name, file_path in generated_files.items():
            if file_path.suffix == ".py":
                # Add the parent directory of this Python file
                python_dirs.add(file_path.parent)

        # For each directory with Python files, ensure __init__.py exists
        for dir_path in python_dirs:
            init_path = dir_path / "__init__.py"

            # Skip if __init__.py was already generated as part of blueprints
            if init_path in generated_files.values():
                continue

            # Create __init__.py if it doesn't exist or if force is True
            if not init_path.exists() or force:
                # Create empty __init__.py file
                init_path.write_text("")

                # Generate a module name for tracking
                # Use the directory name as a simple key
                module_key = f"{dir_path.name}.__init__"
                init_files[module_key] = init_path

        return init_files

    def _find_project_root(
        self, resolved: ResolvedBlueprint, main_md_path: Optional[Path] = None
    ) -> Path:
        """Find the project root directory by looking for main.md."""
        # If main_md_path is provided explicitly, use its directory
        if main_md_path:
            return main_md_path.parent

        # Look through all blueprints to find main.md or similar project root
        for blueprint in resolved.generation_order:
            if blueprint.file_path and blueprint.file_path.name == "main.md":
                return blueprint.file_path.parent

        # If no main.md found, use the main blueprint's directory
        if resolved.main.file_path:
            return resolved.main.file_path.parent

        # Fallback to current directory
        return Path.cwd()

    def _find_main_md_in_project(self, start_path: Path) -> Optional[Path]:
        """Find main.md by walking up the directory tree from start_path."""
        current_path = start_path.resolve()

        # Walk up the directory tree
        while current_path != current_path.parent:  # Stop at filesystem root
            main_md = current_path / "main.md"
            if main_md.exists():
                return main_md
            current_path = current_path.parent

        # Check filesystem root as well
        main_md = current_path / "main.md"
        if main_md.exists():
            return main_md

        return None

    def _generate_makefile(
        self,
        resolved: ResolvedBlueprint,
        output_dir: Path,
        language: str,
        force: bool,
        main_md_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Generate a Makefile with project setup and run commands based on main.md."""
        # Find main.md blueprint for project setup info
        main_md_blueprint = None

        # If main_md_path is provided, parse it directly
        if main_md_path and main_md_path.exists():
            from .parser import BlueprintParser

            parser = BlueprintParser()
            main_md_blueprint = parser.parse_file(main_md_path)
        else:
            # Look for main.md in resolved blueprints
            for blueprint in resolved.generation_order:
                if blueprint.file_path and blueprint.file_path.name == "main.md":
                    main_md_blueprint = blueprint
                    break

        # If no main.md found, use the main blueprint
        setup_blueprint = main_md_blueprint if main_md_blueprint else resolved.main

        # Find the actual app entrypoint module
        app_module = None
        for blueprint in resolved.generation_order:
            if blueprint.file_path and blueprint.file_path.name == "app.md":
                app_module = blueprint.file_path.stem  # "app"
                break
        if not app_module and resolved.main.file_path:
            # Use the main blueprint's module name if no app.md found
            app_module = resolved.main.file_path.stem

        # Extract project setup information from main blueprint
        dependencies = []
        dev_dependencies = []
        install_commands = []
        run_commands = []
        env_vars = []

        # Parse setup blueprint content for dependencies and setup info
        content_lines = setup_blueprint.raw_content.split("\n")
        in_third_party = False
        in_dev_deps = False
        in_installation = False
        in_running = False

        for line in content_lines:
            line = line.strip()

            if ("## Third-party Dependencies" in line or "Dependencies:" in line or 
                "Dependencies to Install:" in line):
                in_third_party = True
                in_dev_deps = False
                in_installation = False
                in_running = False
                continue
            elif "## Development Dependencies" in line or "Development Dependencies:" in line:
                in_third_party = False
                in_dev_deps = True
                in_installation = False
                in_running = False
                continue
            elif "## Installation" in line or "## Installation & Setup" in line:
                in_third_party = False
                in_dev_deps = False
                in_installation = True
                in_running = False
                continue
            elif "## Running" in line or "## Running the Application" in line:
                in_third_party = False
                in_dev_deps = False
                in_installation = False
                in_running = True
                continue
            elif (line.startswith("##") or line.startswith("# ") or 
                  (line.endswith(":") and not line.startswith("-"))):
                in_third_party = False
                in_dev_deps = False
                in_installation = False
                in_running = False
                continue

            if in_third_party and line.startswith("- "):
                # Extract dependency, handle both formats:
                # Old: - fastapi>=0.104.0 # comment
                # New: - fastapi - Web framework
                dep = line[2:].split("#")[0].strip()
                if " - " in dep:
                    # New format: extract just the package name
                    dep = dep.split(" - ")[0].strip()
                if dep:
                    dependencies.append(dep)
            elif in_dev_deps and line.startswith("- "):
                # Extract dev dependency, handle both formats
                dep = line[2:].split("#")[0].strip()
                if " - " in dep:
                    # New format: extract just the package name
                    dep = dep.split(" - ")[0].strip()
                if dep:
                    dev_dependencies.append(dep)
            elif in_installation and (
                line.startswith("pip install")
                or line.startswith("uv")
                or line.startswith("npm")
            ):
                install_commands.append(line)
            elif in_installation and line.startswith("export"):
                env_vars.append(line)
            elif in_running and (
                line.startswith("uvicorn")
                or line.startswith("python")
                or line.startswith("npm")
                or line.startswith("node")
            ):
                run_commands.append(line)

        # Generate Makefile content
        makefile_content = self._create_makefile_content(
            setup_blueprint.module_name,
            dependencies,
            dev_dependencies,
            install_commands,
            run_commands,
            env_vars,
            language,
            app_module,
        )

        if not makefile_content.strip():
            return None

        makefile_path = output_dir / "Makefile"

        # Check if file exists and force flag
        if makefile_path.exists() and not force:
            return None

        makefile_path.write_text(makefile_content)
        return makefile_path

    def _create_makefile_content(
        self,
        project_name: str,
        dependencies: list,
        dev_dependencies: list,
        install_commands: list,
        run_commands: list,
        env_vars: list,
        language: str,
        app_module: Optional[str] = None,
    ) -> str:
        """Create Makefile content based on project information."""

        lines = [
            f"# Makefile for {project_name}",
            f"# Generated by blueprints.md",
            "",
            ".PHONY: help install install-dev setup run dev test clean",
            "",
            "help:",
            "\t@echo 'Available commands:'",
            "\t@echo '  install     - Install production dependencies'",
            "\t@echo '  install-dev - Install development dependencies'",
            "\t@echo '  setup       - Complete project setup'",
            "\t@echo '  run         - Run the application'",
            "\t@echo '  dev         - Run in development mode'",
            "\t@echo '  test        - Run tests'",
            "\t@echo '  clean       - Clean up generated files'",
            "",
        ]

        # Requirements file generation
        if dependencies:
            lines.extend(
                [
                    "requirements.txt:",
                    "\t@echo 'Generating requirements.txt...'",
                    "\t@echo '# Production dependencies' > requirements.txt",
                ]
            )
            for dep in dependencies:
                lines.append(f"\t@echo '{dep}' >> requirements.txt")
            lines.append("")

        if dev_dependencies:
            lines.extend(
                [
                    "requirements-dev.txt:",
                    "\t@echo 'Generating requirements-dev.txt...'",
                    "\t@echo '# Development dependencies' > requirements-dev.txt",
                ]
            )
            for dep in dev_dependencies:
                lines.append(f"\t@echo '{dep}' >> requirements-dev.txt")
            lines.append("")

        # Install commands
        if language.lower() == "python":
            if dependencies:
                lines.extend(
                    [
                        "install: requirements.txt",
                        "\t@echo 'Installing production dependencies...'",
                        "\tpip install -r requirements.txt",
                        "",
                    ]
                )

            if dev_dependencies:
                lines.extend(
                    [
                        "install-dev: requirements-dev.txt",
                        "\t@echo 'Installing development dependencies...'",
                        "\tpip install -r requirements-dev.txt",
                        "",
                    ]
                )
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend(
                [
                    "install:",
                    "\t@echo 'Installing dependencies...'",
                    "\tnpm install",
                    "",
                    "install-dev:",
                    "\t@echo 'Installing development dependencies...'",
                    "\tnpm install --include=dev",
                    "",
                ]
            )

        # Setup command
        setup_deps = []
        if dependencies:
            setup_deps.append("install")
        if dev_dependencies:
            setup_deps.append("install-dev")

        if setup_deps:
            lines.extend(
                [
                    f"setup: {' '.join(setup_deps)}",
                    "\t@echo 'Project setup complete!'",
                    "\t@echo 'Environment variables to set:'",
                ]
            )
            for env_var in env_vars:
                lines.append(f"\t@echo '  {env_var}'")
            lines.append("")

        # Run commands
        if run_commands:
            prod_cmd = run_commands[0] if run_commands else ""
            dev_cmd = (
                run_commands[1]
                if len(run_commands) > 1
                else run_commands[0] if run_commands else ""
            )

            if prod_cmd:
                lines.extend(
                    ["run:", "\t@echo 'Starting application...'", f"\t{prod_cmd}", ""]
                )

            if dev_cmd:
                lines.extend(
                    [
                        "dev:",
                        "\t@echo 'Starting development server...'",
                        f"\t{dev_cmd}",
                        "",
                    ]
                )
        else:
            # Default run commands based on language
            if language.lower() == "python":
                # Use app_module if provided, otherwise fall back to project_name
                module_to_run = app_module if app_module else project_name
                lines.extend(
                    [
                        "run:",
                        f"\t@echo 'Starting {module_to_run}...'",
                        f"\tpython -m {module_to_run}",
                        "",
                        "dev:",
                        f"\t@echo 'Starting {module_to_run} in development mode...'",
                        f"\tpython -m {module_to_run} --reload",
                        "",
                    ]
                )
            elif language.lower() in ["javascript", "typescript"]:
                lines.extend(
                    [
                        "run:",
                        "\t@echo 'Starting application...'",
                        "\tnpm start",
                        "",
                        "dev:",
                        "\t@echo 'Starting development server...'",
                        "\tnpm run dev",
                        "",
                    ]
                )

        # Test command
        if language.lower() == "python":
            lines.extend(["test:", "\t@echo 'Running tests...'", "\tpytest", ""])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend(["test:", "\t@echo 'Running tests...'", "\tnpm test", ""])

        # Clean command
        if language.lower() == "python":
            lines.extend(
                [
                    "clean:",
                    "\t@echo 'Cleaning up...'",
                    "\tfind . -type f -name '*.pyc' -delete",
                    "\tfind . -type d -name '__pycache__' -delete",
                    "\trm -f requirements.txt requirements-dev.txt",
                    "",
                ]
            )
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend(
                [
                    "clean:",
                    "\t@echo 'Cleaning up...'",
                    "\trm -rf node_modules",
                    "\trm -f package-lock.json",
                    "",
                ]
            )

        return "\n".join(lines)

    def generate_with_verification(
        self,
        blueprint: "Blueprint",
        context_parts: List[str],
        language: str = "python",
        max_retries: int = 3,
        project_root: Optional[Path] = None,
        main_md_path: Optional[Path] = None,
    ) -> Tuple[str, List["VerificationResult"]]:
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

    def generate_single_blueprint(
        self,
        blueprint: "Blueprint",
        context_parts: List[str],
        language: str = "python",
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate code for a single blueprint with context."""
        prompt = self._create_single_blueprint_prompt(
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
