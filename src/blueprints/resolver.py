"""Simple blueprint dependency resolver without complex algorithms."""

from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass, field

from .parser import Blueprint, BlueprintReference, BlueprintParser


@dataclass
class ResolvedBlueprint:
    """A blueprint with its dependencies resolved."""
    main: Blueprint
    dependencies: List[Blueprint]
    generation_order: List[Blueprint] = field(default=None)
    
    def __post_init__(self):
        # If generation_order is not provided, create a simple order
        if self.generation_order is None:
            self.generation_order = self.dependencies + [self.main]


class BlueprintResolver:
    """Simple, fast dependency resolver for blueprint files."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.parser = BlueprintParser()

    def resolve(self, blueprint_path: Path) -> ResolvedBlueprint:
        """Resolve blueprint dependencies using simple depth-first discovery."""
        main_blueprint = self.parser.parse_file(blueprint_path)
        dependencies = self._resolve_dependencies(main_blueprint, set())
        
        return ResolvedBlueprint(
            main=main_blueprint,
            dependencies=list(dependencies.values())
        )

    def _resolve_dependencies(
        self, blueprint: Blueprint, visited: Set[str]
    ) -> dict[str, Blueprint]:
        """Recursively discover dependencies depth-first."""
        dependencies = {}
        
        if blueprint.module_name in visited:
            return dependencies
            
        visited.add(blueprint.module_name)
        
        for ref in blueprint.blueprint_refs:
            dep_blueprint = self._resolve_reference(ref, blueprint)
            if dep_blueprint and dep_blueprint.module_name not in dependencies:
                dependencies[dep_blueprint.module_name] = dep_blueprint
                # Recursively get sub-dependencies
                sub_deps = self._resolve_dependencies(dep_blueprint, visited)
                dependencies.update(sub_deps)
        
        return dependencies

    def _resolve_reference(
        self, ref: BlueprintReference, from_blueprint: Blueprint
    ) -> Optional[Blueprint]:
        """Find and load blueprint from reference."""
        module_path = ref.module_path
        
        # Fix parser bug where @../path becomes ..path instead of ../path
        if module_path.startswith("..") and not module_path.startswith("../"):
            module_path = "../" + module_path[2:]
        
        # Handle relative imports
        if module_path.startswith("."):
            module_path = self._resolve_relative_path(module_path, from_blueprint)
        
        blueprint_file = self._find_blueprint_file(module_path)
        if blueprint_file:
            return self._load_blueprint(blueprint_file)
        
        return None

    def _resolve_relative_path(
        self, relative_path: str, from_blueprint: Blueprint
    ) -> str:
        """Convert relative import to absolute path."""
        if not from_blueprint.file_path:
            return relative_path
            
        current_dir = from_blueprint.file_path.parent
        
        # Handle ../ style paths
        if relative_path.startswith("../"):
            parts = relative_path.split("/")
            remaining_parts = []
            # Process parts: go up for .. and collect the rest
            for part in parts:
                if part == "..":
                    current_dir = current_dir.parent
                elif part:  # Non-empty part
                    remaining_parts.append(part)
            # Return the remaining path parts
            return "/".join(remaining_parts) if remaining_parts else current_dir.name
        
        # Handle ./style paths
        elif relative_path.startswith("./"):
            return relative_path[2:]  # Remove ./
            
        # Handle single dots (current directory reference)
        elif relative_path.startswith("."):
            level = len(relative_path) - len(relative_path.lstrip("."))
            for _ in range(level - 1):
                current_dir = current_dir.parent
            module_part = relative_path[level:]
            if module_part:
                return f"{current_dir.name}.{module_part}"
            return current_dir.name
        
        return relative_path

    def _find_blueprint_file(self, module_path: str) -> Optional[Path]:
        """Find blueprint file by module path."""
        # Handle both dot-separated and slash-separated paths
        if "." in module_path:
            path_parts = module_path.split(".")
            slash_path = "/".join(path_parts)
        else:
            slash_path = module_path.replace(".", "/")
            path_parts = module_path.split("/")
        
        # Try common file path patterns
        candidates = [
            self.project_root / f"{slash_path}.md",  # api/tasks.md
            self.project_root / f"{module_path}.md",  # api.tasks.md (less common)
            self.project_root / slash_path / f"{path_parts[-1]}.md",  # api/tasks/tasks.md
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
                
        return None

    def _load_blueprint(self, file_path: Path) -> Optional[Blueprint]:
        """Load blueprint from file with basic error handling."""
        try:
            return self.parser.parse_file(file_path)
        except Exception:
            return None

    def get_context_for_generation(self, resolved: ResolvedBlueprint) -> str:
        """Create context string for code generation."""
        context_parts = []
        
        # Add dependencies first
        if resolved.dependencies:
            context_parts.append("=== REFERENCED BLUEPRINTS ===\n")
            for dep in resolved.dependencies:
                context_parts.append(f"--- {dep.module_name} ---")
                context_parts.append(dep.raw_content.strip())
                context_parts.append("")
        
        # Add main blueprint
        context_parts.append("=== MAIN BLUEPRINT TO IMPLEMENT ===\n")
        context_parts.append(resolved.main.raw_content.strip())
        
        return "\n".join(context_parts)

    def get_dependencies_for_blueprint(
        self, blueprint: Blueprint, resolved: ResolvedBlueprint
    ) -> List[Blueprint]:
        """Get direct dependencies for a blueprint."""
        dependencies = []
        
        # Find blueprints that this blueprint directly references
        for ref in blueprint.blueprint_refs:
            dep_blueprint = self._resolve_reference(ref, blueprint)
            if dep_blueprint:
                dependencies.append(dep_blueprint)
        
        return dependencies