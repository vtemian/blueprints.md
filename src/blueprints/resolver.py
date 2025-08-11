"""Blueprint resolver for handling nested dependencies and references."""

from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict

from .parser import Blueprint, BlueprintReference
from .natural_parser import HybridBlueprintParser as BlueprintParser


@dataclass
class ResolvedBlueprint:
    """A blueprint with all its dependencies resolved."""

    main: Blueprint
    dependencies: List[Blueprint] = field(default_factory=list)
    dependency_graph: Dict[str, Set[str]] = field(default_factory=dict)
    generation_order: List[Blueprint] = field(
        default_factory=list
    )  # Topologically sorted


class BlueprintResolver:
    """Resolves blueprint dependencies and creates a complete context."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize resolver with optional project root."""
        self.project_root = project_root or Path.cwd()
        self.parser = BlueprintParser()
        self._cache: Dict[str, Blueprint] = {}
        self._blueprint_map: Dict[str, Path] = {}

    def resolve(self, blueprint_path: Path) -> ResolvedBlueprint:
        """Resolve a blueprint and all its dependencies."""
        # Parse the main blueprint
        main_blueprint = self.parser.parse_file(blueprint_path)

        # Build blueprint map if not already done
        if not self._blueprint_map:
            self._build_blueprint_map()

        # Resolve all dependencies recursively
        resolved_deps = self._resolve_dependencies(main_blueprint, set())

        # Build dependency graph
        all_blueprints = {main_blueprint.module_name: main_blueprint}
        all_blueprints.update(resolved_deps)
        dep_graph = self._build_dependency_graph(main_blueprint, resolved_deps)

        # Calculate generation order using topological sort
        generation_order = self._topological_sort(all_blueprints, dep_graph)

        return ResolvedBlueprint(
            main=main_blueprint,
            dependencies=list(resolved_deps.values()),
            dependency_graph=dep_graph,
            generation_order=generation_order,
        )

    def _build_blueprint_map(self) -> None:
        """Build a map of module names to blueprint file paths."""
        # Find all .md files in project
        for md_file in self.project_root.rglob("*.md"):
            # Skip non-blueprint files
            if md_file.name in ["README.md", "CLAUDE.md", "BLUEPRINTS_SPEC.md"]:
                continue

            try:
                # Parse to get module name
                blueprint = self._load_blueprint(md_file)
                if blueprint:
                    self._blueprint_map[blueprint.module_name] = md_file
            except Exception:
                # Skip files that can't be parsed as blueprints
                pass

    def _resolve_dependencies(
        self, blueprint: Blueprint, visited: Set[str]
    ) -> Dict[str, Blueprint]:
        """Recursively resolve all blueprint dependencies."""
        resolved = {}

        # Avoid circular dependencies
        if blueprint.module_name in visited:
            return resolved

        visited.add(blueprint.module_name)

        # Process each blueprint reference
        for ref in blueprint.blueprint_refs:
            dep_blueprint = self._resolve_reference(ref, blueprint)
            if dep_blueprint and dep_blueprint.module_name not in resolved:
                resolved[dep_blueprint.module_name] = dep_blueprint
                # Recursively resolve dependencies
                sub_deps = self._resolve_dependencies(dep_blueprint, visited)
                resolved.update(sub_deps)

        return resolved

    def _resolve_reference(
        self, ref: BlueprintReference, from_blueprint: Blueprint
    ) -> Optional[Blueprint]:
        """Resolve a blueprint reference to an actual blueprint."""
        module_path = ref.module_path

        # Handle relative imports
        if module_path.startswith("."):
            # Calculate absolute module path based on current blueprint's location
            module_path = self._resolve_relative_import(module_path, from_blueprint)

        # Look up in blueprint map
        if module_path in self._blueprint_map:
            return self._load_blueprint(self._blueprint_map[module_path])

        # Try to find by file path
        blueprint_file = self._find_blueprint_file(module_path)
        if blueprint_file:
            return self._load_blueprint(blueprint_file)

        return None

    def _resolve_relative_import(
        self, relative_path: str, from_blueprint: Blueprint
    ) -> str:
        """Convert relative import to absolute module path."""
        if not from_blueprint.file_path:
            return relative_path

        # Get the directory of the current blueprint
        current_dir = from_blueprint.file_path.parent

        # Count leading dots
        level = 0
        for char in relative_path:
            if char == ".":
                level += 1
            else:
                break

        # Navigate up directories
        for _ in range(level - 1):
            current_dir = current_dir.parent

        # Get the module part after dots
        module_part = relative_path[level:]

        # Construct absolute module path
        if module_part:
            return f"{current_dir.name}.{module_part}"
        else:
            return current_dir.name

    def _find_blueprint_file(self, module_path: str) -> Optional[Path]:
        """Find blueprint file by module path."""
        # Convert module path to potential file paths
        path_parts = module_path.split(".")

        # Try different combinations
        potential_files = [
            self.project_root / f"{module_path}.md",
            self.project_root / f"{'/'.join(path_parts)}.md",
            self.project_root / f"{'/'.join(path_parts)}" / f"{path_parts[-1]}.md",
        ]

        for file_path in potential_files:
            if file_path.exists():
                return file_path

        return None

    def _load_blueprint(self, file_path: Path) -> Optional[Blueprint]:
        """Load and cache a blueprint from file."""
        str_path = str(file_path)
        if str_path in self._cache:
            return self._cache[str_path]

        try:
            blueprint = self.parser.parse_file(file_path)
            self._cache[str_path] = blueprint
            return blueprint
        except Exception:
            return None

    def _build_dependency_graph(
        self, main: Blueprint, dependencies: Dict[str, Blueprint]
    ) -> Dict[str, Set[str]]:
        """Build a dependency graph showing relationships."""
        graph = {main.module_name: set()}

        # Add main blueprint's dependencies
        for ref in main.blueprint_refs:
            resolved_name = self._get_resolved_module_name(ref, main)
            if resolved_name:
                graph[main.module_name].add(resolved_name)

        # Add dependencies' dependencies
        for dep in dependencies.values():
            graph[dep.module_name] = set()
            for ref in dep.blueprint_refs:
                resolved_name = self._get_resolved_module_name(ref, dep)
                if resolved_name:
                    graph[dep.module_name].add(resolved_name)

        return graph

    def _get_resolved_module_name(
        self, ref: BlueprintReference, from_blueprint: Blueprint
    ) -> Optional[str]:
        """Get the resolved module name for a reference."""
        dep = self._resolve_reference(ref, from_blueprint)
        return dep.module_name if dep else None

    def get_context_for_generation(self, resolved: ResolvedBlueprint) -> str:
        """Create a context string with all blueprints for code generation."""
        context_parts = []

        # Add dependency blueprints first
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

    def _topological_sort(
        self, all_blueprints: Dict[str, Blueprint], graph: Dict[str, Set[str]]
    ) -> List[Blueprint]:
        """Perform topological sort to determine generation order."""
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for node in graph:
            in_degree[node] = 0

        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1

        # Find all nodes with no incoming edges
        queue = deque([node for node in graph if in_degree[node] == 0])
        result = []

        while queue:
            current = queue.popleft()
            if current in all_blueprints:
                result.append(all_blueprints[current])

            # For each neighbor of current node
            for neighbor in graph.get(current, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_dependencies_for_blueprint(
        self, blueprint: Blueprint, resolved: ResolvedBlueprint
    ) -> List[Blueprint]:
        """Get direct dependencies for a specific blueprint."""
        dependencies = []
        blueprint_deps = resolved.dependency_graph.get(blueprint.module_name, set())

        # Find blueprint objects for dependencies
        all_blueprints = {resolved.main.module_name: resolved.main}
        for dep in resolved.dependencies:
            all_blueprints[dep.module_name] = dep

        for dep_name in blueprint_deps:
            if dep_name in all_blueprints:
                dependencies.append(all_blueprints[dep_name])

        return dependencies
