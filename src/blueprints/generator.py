"""Code generator module that uses Claude API to generate code from blueprints."""

import os
from pathlib import Path
from typing import Optional, Dict, List
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
            raise ValueError("Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter.")
        
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
        lines = response.strip().split('\n')
        
        # Check if response is wrapped in code blocks
        if lines[0].startswith('```'):
            # Find the closing code block
            code_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith('```') and not in_code_block:
                    in_code_block = True
                    continue
                elif line.startswith('```') and in_code_block:
                    break
                elif in_code_block:
                    code_lines.append(line)
            return '\n'.join(code_lines)
        
        # If no code blocks, return as is
        return response.strip()
    
    
    def generate_project(self, resolved: ResolvedBlueprint, output_dir: Path, language: str = "python", force: bool = False) -> Dict[str, Path]:
        """Generate code for all blueprints in dependency order with separate API calls."""
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = {}
        generated_context = {}  # Store generated code for dependencies
        
        for blueprint in resolved.generation_order:
            resolver = BlueprintResolver()
            dependencies = resolver.get_dependencies_for_blueprint(blueprint, resolved)
            
            # Create context with only direct dependencies that have been generated
            context_parts = []
            
            if dependencies:
                context_parts.extend([
                    "You have access to the following dependency modules:",
                    ""
                ])
                
                for dep in dependencies:
                    if dep.module_name in generated_context:
                        context_parts.extend([
                            f"=== Module: {dep.module_name} ===",
                            f"Blueprint:",
                            dep.raw_content.strip(),
                            "",
                            f"Generated code:",
                            generated_context[dep.module_name],
                            ""
                        ])
                
                context_parts.extend([
                    "=== END OF DEPENDENCIES ===",
                    "",
                    f"Now generate {language} code for the following blueprint:",
                    ""
                ])
            else:
                context_parts.extend([
                    f"Generate {language} code from this blueprint:",
                    ""
                ])
            
            # Create prompt for this specific blueprint
            prompt = self._create_single_blueprint_prompt(blueprint, language, context_parts)
            
            # Generate code for this blueprint
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                code = self._extract_code_from_response(response.content[0].text)
                
                # Determine output file path - same directory as blueprint
                if blueprint.file_path:
                    # Generate in same directory as blueprint file
                    blueprint_dir = blueprint.file_path.parent
                    filename = f"{blueprint.file_path.stem}{self._get_file_extension(language)}"
                    output_path = blueprint_dir / filename
                else:
                    # Fallback to output_dir structure
                    module_parts = blueprint.module_name.split('.')
                    filename = f"{module_parts[-1]}{self._get_file_extension(language)}"
                    
                    if len(module_parts) > 1:
                        file_dir = output_dir / Path(*module_parts[:-1])
                        file_dir.mkdir(parents=True, exist_ok=True)
                        output_path = file_dir / filename
                    else:
                        output_path = output_dir / filename
                
                # Check if file exists and force flag
                if output_path.exists() and not force:
                    raise RuntimeError(f"File {output_path} already exists. Use --force to overwrite.")
                
                # Save the code
                output_path.write_text(code)
                generated_files[blueprint.module_name] = output_path
                generated_context[blueprint.module_name] = code
                
            except Exception as e:
                raise RuntimeError(f"Failed to generate code for {blueprint.module_name}: {str(e)}")
        
        # Generate Makefile with project setup instructions
        makefile_path = self._generate_makefile(resolved, output_dir, language, force)
        if makefile_path:
            generated_files["Makefile"] = makefile_path
        
        return generated_files
    
    def generate_single_with_context(self, resolved: ResolvedBlueprint, output_path: Path, language: str = "python", force: bool = False) -> Path:
        """Generate a single file with all dependencies as context in one API call."""
        # Create comprehensive context with all dependencies
        context_parts = []
        
        if resolved.dependencies:
            context_parts.extend([
                "You have access to the following blueprint dependencies:",
                ""
            ])
            
            for dep in resolved.dependencies:
                context_parts.extend([
                    f"=== Blueprint: {dep.module_name} ===",
                    dep.raw_content.strip(),
                    ""
                ])
            
            context_parts.extend([
                "=== END OF DEPENDENCIES ===",
                "",
                f"Now generate {language} code for the following blueprint, using the above blueprints as context:",
                ""
            ])
        else:
            context_parts.extend([
                f"Generate {language} code from this blueprint:",
                ""
            ])
        
        # Create prompt for the main blueprint
        prompt = self._create_single_blueprint_prompt(resolved.main, language, context_parts)
        
        # Generate code with full context
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
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
            raise RuntimeError(f"Failed to generate code for {resolved.main.module_name}: {str(e)}")
    
    def _create_single_blueprint_prompt(self, blueprint: Blueprint, language: str, context_parts: List[str]) -> str:
        """Create a prompt for generating a single blueprint."""
        prompt_parts = context_parts.copy()
        
        prompt_parts.extend([
            f"Module: {blueprint.module_name}",
            f"Description: {blueprint.description}",
            ""
        ])
        
        # Format components
        if blueprint.components:
            prompt_parts.append("Components to implement:")
            for component in blueprint.components:
                prompt_parts.extend(self._format_component_for_prompt(component))
        
        # Add notes
        if blueprint.notes:
            prompt_parts.extend([
                "",
                "Implementation notes:",
                *[f"- {note}" for note in blueprint.notes],
            ])
        
        prompt_parts.extend([
            "",
            f"Generate complete {language} code with:",
            "1. Automatically infer and add all necessary imports (standard library, third-party, and local)",
            "2. Full implementation of all components", 
            "3. Type hints and concise docstrings",
            "4. Error handling where appropriate",
            "5. Follow the implementation notes",
            "",
            "Import Requirements:",
            "- Import only what you actually use in the code",
            "- Use standard library imports when possible", 
            "- Infer third-party packages from the component descriptions and functionality",
            "- Group imports: standard library, third-party, then local imports",
            "",
            "Return ONLY the code without explanations or tests."
        ])
        
        return "\n".join(prompt_parts)
    
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
            "c": ".c"
        }
        return extensions.get(language.lower(), ".txt")
    
    def _generate_makefile(self, resolved: ResolvedBlueprint, output_dir: Path, language: str, force: bool) -> Optional[Path]:
        """Generate a Makefile with project setup and run commands based on main blueprint."""
        main_blueprint = resolved.main
        
        # Extract project setup information from main blueprint
        dependencies = []
        dev_dependencies = []
        install_commands = []
        run_commands = []
        env_vars = []
        
        # Parse main blueprint content for dependencies and setup info
        content_lines = main_blueprint.raw_content.split('\n')
        in_third_party = False
        in_dev_deps = False
        in_installation = False
        in_running = False
        
        for line in content_lines:
            line = line.strip()
            
            if "## Third-party Dependencies" in line:
                in_third_party = True
                in_dev_deps = False
                in_installation = False
                in_running = False
                continue
            elif "## Development Dependencies" in line:
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
            elif line.startswith("##") or line.startswith("# "):
                in_third_party = False
                in_dev_deps = False
                in_installation = False
                in_running = False
                continue
            
            if in_third_party and line.startswith("- "):
                # Extract dependency
                dep = line[2:].split("#")[0].strip()
                if dep:
                    dependencies.append(dep)
            elif in_dev_deps and line.startswith("- "):
                # Extract dev dependency
                dep = line[2:].split("#")[0].strip()
                if dep:
                    dev_dependencies.append(dep)
            elif in_installation and (line.startswith("pip install") or line.startswith("uv") or line.startswith("npm")):
                install_commands.append(line)
            elif in_installation and line.startswith("export"):
                env_vars.append(line)
            elif in_running and (line.startswith("uvicorn") or line.startswith("python") or line.startswith("npm") or line.startswith("node")):
                run_commands.append(line)
        
        # Generate Makefile content
        makefile_content = self._create_makefile_content(
            main_blueprint.module_name,
            dependencies,
            dev_dependencies,
            install_commands,
            run_commands,
            env_vars,
            language
        )
        
        if not makefile_content.strip():
            return None
        
        makefile_path = output_dir / "Makefile"
        
        # Check if file exists and force flag
        if makefile_path.exists() and not force:
            return None
        
        makefile_path.write_text(makefile_content)
        return makefile_path
    
    def _create_makefile_content(self, project_name: str, dependencies: list, dev_dependencies: list, 
                                install_commands: list, run_commands: list, env_vars: list, language: str) -> str:
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
            ""
        ]
        
        # Requirements file generation
        if dependencies:
            lines.extend([
                "requirements.txt:",
                "\t@echo 'Generating requirements.txt...'",
                "\t@echo '# Production dependencies' > requirements.txt"
            ])
            for dep in dependencies:
                lines.append(f"\t@echo '{dep}' >> requirements.txt")
            lines.append("")
        
        if dev_dependencies:
            lines.extend([
                "requirements-dev.txt:",
                "\t@echo 'Generating requirements-dev.txt...'", 
                "\t@echo '# Development dependencies' > requirements-dev.txt"
            ])
            for dep in dev_dependencies:
                lines.append(f"\t@echo '{dep}' >> requirements-dev.txt")
            lines.append("")
        
        # Install commands
        if language.lower() == "python":
            if dependencies:
                lines.extend([
                    "install: requirements.txt",
                    "\t@echo 'Installing production dependencies...'",
                    "\tpip install -r requirements.txt",
                    ""
                ])
            
            if dev_dependencies:
                lines.extend([
                    "install-dev: requirements-dev.txt",
                    "\t@echo 'Installing development dependencies...'", 
                    "\tpip install -r requirements-dev.txt",
                    ""
                ])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend([
                "install:",
                "\t@echo 'Installing dependencies...'",
                "\tnpm install",
                "",
                "install-dev:",
                "\t@echo 'Installing development dependencies...'",
                "\tnpm install --include=dev",
                ""
            ])
        
        # Setup command
        setup_deps = []
        if dependencies:
            setup_deps.append("install")
        if dev_dependencies:
            setup_deps.append("install-dev")
        
        if setup_deps:
            lines.extend([
                f"setup: {' '.join(setup_deps)}",
                "\t@echo 'Project setup complete!'",
                "\t@echo 'Environment variables to set:'"
            ])
            for env_var in env_vars:
                lines.append(f"\t@echo '  {env_var}'")
            lines.append("")
        
        # Run commands
        if run_commands:
            prod_cmd = run_commands[0] if run_commands else ""
            dev_cmd = run_commands[1] if len(run_commands) > 1 else run_commands[0] if run_commands else ""
            
            if prod_cmd:
                lines.extend([
                    "run:",
                    "\t@echo 'Starting application...'",
                    f"\t{prod_cmd}",
                    ""
                ])
            
            if dev_cmd:
                lines.extend([
                    "dev:",
                    "\t@echo 'Starting development server...'", 
                    f"\t{dev_cmd}",
                    ""
                ])
        else:
            # Default run commands based on language
            if language.lower() == "python":
                lines.extend([
                    "run:",
                    f"\t@echo 'Starting {project_name}...'",
                    f"\tpython -m {project_name}",
                    "",
                    "dev:",
                    f"\t@echo 'Starting {project_name} in development mode...'",
                    f"\tpython -m {project_name} --reload",
                    ""
                ])
            elif language.lower() in ["javascript", "typescript"]:
                lines.extend([
                    "run:",
                    "\t@echo 'Starting application...'",
                    "\tnpm start",
                    "",
                    "dev:",
                    "\t@echo 'Starting development server...'",
                    "\tnpm run dev",
                    ""
                ])
        
        # Test command
        if language.lower() == "python":
            lines.extend([
                "test:",
                "\t@echo 'Running tests...'",
                "\tpytest",
                ""
            ])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend([
                "test:",
                "\t@echo 'Running tests...'",
                "\tnpm test",
                ""
            ])
        
        # Clean command
        if language.lower() == "python":
            lines.extend([
                "clean:",
                "\t@echo 'Cleaning up...'",
                "\tfind . -type f -name '*.pyc' -delete",
                "\tfind . -type d -name '__pycache__' -delete",
                "\trm -f requirements.txt requirements-dev.txt",
                ""
            ])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend([
                "clean:",
                "\t@echo 'Cleaning up...'",
                "\trm -rf node_modules",
                "\trm -f package-lock.json",
                ""
            ])
        
        return "\n".join(lines)