"""Prompt building utilities for blueprint code generation."""

from typing import Dict, List, Optional
from pathlib import Path

from .parser import Blueprint, Component


class PromptBuilder:
    """Builds prompts for Claude API calls from blueprints and context."""

    def build_single_blueprint_prompt(
        self,
        blueprint: Blueprint,
        language: str,
        context_parts: List[str],
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build a complete prompt for single blueprint generation."""
        prompt_parts = context_parts.copy()
        
        prompt_parts.extend([
            f"Module: {blueprint.module_name}",
            f"Description: {blueprint.description}",
            "",
        ])

        if dependency_versions:
            prompt_parts.extend([
                "Third-party dependency versions to target:",
                *[f"- {name}: {version}" for name, version in dependency_versions.items()],
                "",
            ])

        if blueprint.components:
            prompt_parts.append("Components to implement:")
            for component in blueprint.components:
                prompt_parts.extend(self._format_component_for_prompt(component))

        if blueprint.notes:
            prompt_parts.extend([
                "",
                "Implementation notes:",
                *[f"- {note}" for note in blueprint.notes],
            ])

        blueprint_import_requirements = self._format_blueprint_imports(
            blueprint.blueprint_refs, blueprint.module_name
        )
        
        function_signatures = self._extract_function_signatures(blueprint)
        
        prompt_parts.extend(self._build_generation_guidelines(
            language, blueprint_import_requirements, function_signatures
        ))

        return "\n".join(prompt_parts)

    def build_natural_blueprint_prompt(
        self,
        blueprint: Blueprint,
        language: str,
        context_parts: List[str],
        dependency_versions: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build prompt for natural language blueprints."""
        prompt_parts = context_parts.copy()

        prompt_parts.extend([
            f"Module: {blueprint.module_name}",
            f"Description: {blueprint.description}",
            "",
        ])

        if blueprint.dependencies:
            prompt_parts.extend([
                "Dependencies:",
                *[f"- {dep}" for dep in blueprint.dependencies],
                "",
            ])

        if dependency_versions:
            prompt_parts.extend([
                "Third-party dependency versions to target:",
                *[f"- {name}: {version}" for name, version in dependency_versions.items()],
                "",
            ])

        if blueprint.requirements:
            prompt_parts.extend([
                "Requirements:",
                *[f"- {req}" for req in blueprint.requirements],
                "",
            ])

        for section_name, content in blueprint.sections.items():
            if section_name not in ["dependencies", "requirements"]:
                prompt_parts.extend([
                    f"{section_name.title()}:",
                    *[f"- {item}" if not item.startswith("-") else item for item in content],
                    "",
                ])

        blueprint_import_requirements = self._format_natural_blueprint_imports(
            [ref.module_path for ref in blueprint.blueprint_refs], blueprint.module_name
        )

        prompt_parts.extend(self._build_natural_generation_guidelines(
            language, blueprint_import_requirements
        ))

        return "\n".join(prompt_parts)

    def _format_component_for_prompt(self, component: Component) -> List[str]:
        """Format a single component for inclusion in prompt."""
        parts = [""]

        if component.type == "class":
            header = f"Class {component.name}"
            if component.base_class:
                header += f"({component.base_class})"
            parts.append(header + ":")

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
            if component.methods:
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

    def _format_blueprint_imports(
        self, blueprint_refs: List, current_module: Optional[str] = None
    ) -> str:
        """Format blueprint import requirements."""
        if not blueprint_refs:
            return ""

        lines = ["", "BLUEPRINT DEPENDENCY REQUIREMENTS - MUST MATCH EXACTLY:"]
        for ref in blueprint_refs:
            module_path = self._clean_module_path(ref.module_path, current_module)
            
            for item in ref.items:
                if " as " in item:
                    orig_item, alias = item.split(" as ")
                    expected_import = f"from {module_path} import {orig_item.strip()} as {alias.strip()}"
                    lines.append(f"- {ref.module_path}[{item}] → {expected_import}")
                else:
                    expected_import = f"from {module_path} import {item.strip()}"
                    lines.append(f"- {ref.module_path}[{item}] → {expected_import}")

        return "\n".join(lines)

    def _format_natural_blueprint_imports(
        self, blueprint_refs: List[str], current_module: Optional[str] = None
    ) -> str:
        """Format natural blueprint import requirements."""
        if not blueprint_refs:
            return ""

        lines = ["", "BLUEPRINT DEPENDENCY REQUIREMENTS:"]
        for ref in blueprint_refs:
            clean_ref = ref.lstrip("@").lstrip("./")
            if clean_ref.startswith("../"):
                clean_ref = clean_ref[3:]
            
            lines.append(
                f"- {ref} → Analyze this blueprint and import the necessary components"
            )

        return "\n".join(lines)

    def _clean_module_path(self, module_path: str, current_module: Optional[str]) -> str:
        """Clean and normalize module path for imports."""
        if module_path.startswith(".."):
            return module_path[2:]
        elif module_path.startswith("."):
            if current_module and "." in current_module:
                parent_namespace = ".".join(current_module.split(".")[:-1])
                sibling_module = module_path[1:]
                return f"{parent_namespace}.{sibling_module}"
            else:
                return module_path[1:]
        return module_path

    def _extract_function_signatures(self, blueprint: Blueprint) -> str:
        """Extract function signatures to clarify async/sync nature."""
        if not blueprint.components:
            return ""

        signatures = ["Function signatures from blueprint (all are SYNC unless marked otherwise):"]
        
        for component in blueprint.components:
            if component.type == "function" and component.methods:
                method = component.methods[0]
                sig = f"- {method.name}("
                if method.params:
                    sig += method.params
                sig += ")"
                if method.return_type:
                    sig += f" -> {method.return_type}"
                    
                if method.is_async:
                    sig += " # ASYNC function - use await when calling"
                else:
                    sig += " # SYNC function - do NOT use await when calling"
                signatures.append(sig)

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

        return "\n".join(signatures) if len(signatures) > 1 else ""

    def _build_generation_guidelines(
        self, language: str, blueprint_import_requirements: str, function_signatures: str
    ) -> List[str]:
        """Build the standard generation guidelines."""
        return [
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

    def _build_natural_generation_guidelines(
        self, language: str, blueprint_import_requirements: str
    ) -> List[str]:
        """Build generation guidelines for natural language blueprints."""
        return [
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