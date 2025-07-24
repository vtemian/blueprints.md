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
        
        # Format dependencies (external packages only, not blueprint refs)
        if blueprint.dependencies:
            deps_parts = []
            for package, items in blueprint.dependencies.items():
                if items:
                    deps_parts.append(f"{package}: {', '.join(items)}")
                else:
                    deps_parts.append(package)
            prompt_parts.extend([
                "External dependencies:",
                *[f"- {dep}" for dep in deps_parts],
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
            "1. All necessary imports based on the dependencies",
            "2. Full implementation of all components",
            "3. Type hints and concise docstrings",
            "4. Error handling where appropriate", 
            "5. Follow the implementation notes",
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