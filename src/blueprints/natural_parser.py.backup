"""Natural language blueprint parser for prompt-like .md files."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class NaturalBlueprint:
    """Represents a parsed natural language blueprint file."""

    module_name: str
    description: str = ""
    dependencies: List[str] = field(
        default_factory=list
    )  # All dependencies (external + blueprints)
    blueprint_refs: List[str] = field(default_factory=list)  # Only blueprint references
    requirements: List[str] = field(default_factory=list)
    sections: Dict[str, List[str]] = field(
        default_factory=dict
    )  # Additional sections like "Security", "Performance", etc.
    raw_content: str = ""
    file_path: Optional[Path] = None


class NaturalBlueprintParser:
    """Parses natural language blueprint markdown files into structured data."""

    def parse_file(self, file_path: Path) -> NaturalBlueprint:
        """Parse a blueprint file and return structured data."""
        content = file_path.read_text()
        blueprint = self.parse_content(content)
        blueprint.file_path = file_path
        return blueprint

    def parse_content(self, content: str) -> NaturalBlueprint:
        """Parse natural language blueprint content and return structured data."""
        lines = content.strip().split("\n")

        if not lines or not lines[0].startswith("#"):
            raise ValueError("Blueprint must start with # module.name")

        # Extract module name
        module_name = lines[0].strip("#").strip()

        # Find description (first non-empty line after module name)
        description = ""
        desc_start = 1
        while desc_start < len(lines):
            line = lines[desc_start].strip()
            if line and not line.startswith("#"):
                description = line
                break
            desc_start += 1

        blueprint = NaturalBlueprint(
            module_name=module_name, description=description, raw_content=content
        )

        # Parse sections
        current_section = None
        current_content = []

        for i, line in enumerate(lines[desc_start + 1 :], desc_start + 1):
            line_stripped = line.strip()

            # Detect section headers
            if line_stripped.lower().startswith("dependencies:"):
                self._save_current_section(blueprint, current_section, current_content)
                current_section = "dependencies"
                current_content = []
                # Extract inline dependencies if present
                deps_inline = line_stripped[13:].strip()  # Remove "Dependencies:"
                if deps_inline:
                    current_content.append(deps_inline)

            elif line_stripped.lower().startswith("requirements:"):
                self._save_current_section(blueprint, current_section, current_content)
                current_section = "requirements"
                current_content = []

            elif re.match(
                r"^[A-Z][A-Za-z\s]+:", line_stripped
            ):  # Generic section headers
                self._save_current_section(blueprint, current_section, current_content)
                section_name = line_stripped.split(":")[0].lower()
                current_section = section_name
                current_content = []

            elif line_stripped.startswith("-") and current_section:
                # Bullet point in current section
                current_content.append(line_stripped[1:].strip())

            elif line_stripped and current_section:
                # Regular content in current section
                current_content.append(line_stripped)

        # Save the last section
        self._save_current_section(blueprint, current_section, current_content)

        return blueprint

    def _save_current_section(
        self, blueprint: NaturalBlueprint, section: Optional[str], content: List[str]
    ) -> None:
        """Save the current section content to the blueprint."""
        if not section or not content:
            return

        if section == "dependencies":
            self._parse_dependencies(blueprint, content)
        elif section == "requirements":
            blueprint.requirements = content
        else:
            # Store other sections as-is
            blueprint.sections[section] = content

    def _parse_dependencies(
        self, blueprint: NaturalBlueprint, content: List[str]
    ) -> None:
        """Parse dependencies section and separate external vs blueprint references."""
        for line in content:
            # Split by comma for multiple dependencies on one line
            deps = [dep.strip() for dep in line.split(",")]

            for dep in deps:
                if not dep:
                    continue

                blueprint.dependencies.append(dep)

                # Check if it's a blueprint reference (starts with @ or relative path)
                if dep.startswith("@") or dep.startswith("./") or dep.startswith("../"):
                    blueprint.blueprint_refs.append(dep)


# Adapter to maintain compatibility with existing code
class BlueprintAdapter:
    """Adapts NaturalBlueprint to the existing Blueprint interface."""

    def __init__(self, natural_blueprint: NaturalBlueprint):
        self.natural = natural_blueprint

    @property
    def module_name(self) -> str:
        return self.natural.module_name

    @property
    def description(self) -> str:
        return self.natural.description

    @property
    def blueprint_refs(self) -> List[Any]:
        """Convert blueprint references to the expected format."""
        from .parser import BlueprintReference
        
        refs = []
        for ref in self.natural.blueprint_refs:
            # Clean up the reference and create proper BlueprintReference objects
            clean_ref = ref.lstrip("@").lstrip("./").lstrip("../")
            # Convert relative paths to the format the resolver expects
            if ref.startswith("@./"):
                clean_ref = ref[3:]  # Remove @./
            elif ref.startswith("@../"):
                clean_ref = ".." + ref[4:]  # Keep .. for parent directory
            elif ref.startswith("@"):
                clean_ref = ref[1:]  # Remove @
            
            refs.append(BlueprintReference(module_path=clean_ref, items=[]))
        return refs

    @property
    def components(self) -> List[Any]:
        """Natural blueprints don't have structured components."""
        return []

    @property
    def notes(self) -> List[str]:
        """Extract notes from sections."""
        notes = []
        for section_name, content in self.natural.sections.items():
            if "note" in section_name.lower():
                notes.extend(content)
        return notes

    @property
    def raw_content(self) -> str:
        return self.natural.raw_content

    @property
    def file_path(self) -> Optional[Path]:
        return self.natural.file_path


class HybridBlueprintParser:
    """Parser that handles both old structured and new natural language formats."""

    def __init__(self):
        from .parser import CompactBlueprintParser

        self.structured_parser = CompactBlueprintParser()
        self.natural_parser = NaturalBlueprintParser()

    def parse_file(self, file_path: Path) -> Any:
        """Parse a blueprint file, auto-detecting the format."""
        content = file_path.read_text()

        if self._is_structured_format(content):
            return self.structured_parser.parse_file(file_path)
        else:
            natural = self.natural_parser.parse_file(file_path)
            return BlueprintAdapter(natural)

    def parse_content(self, content: str) -> Any:
        """Parse blueprint content, auto-detecting the format."""
        if self._is_structured_format(content):
            return self.structured_parser.parse_content(content)
        else:
            natural = self.natural_parser.parse_content(content)
            return BlueprintAdapter(natural)

    def _is_structured_format(self, content: str) -> bool:
        """Detect if content uses the old structured format."""
        lines = content.strip().split("\n")

        # Look for structured format indicators
        for line in lines[:20]:  # Check first 20 lines
            line_stripped = line.strip()

            # Old format indicators
            if (
                line_stripped.startswith("deps:")
                or line_stripped.startswith("notes:")
                or re.match(r"^\w+\(.*\):$", line_stripped)  # Function signatures
                or re.match(r"^[A-Z_]+:", line_stripped)  # Constants
                or line_stripped.startswith("- ")
                and ":" in line_stripped
            ):  # Method signatures
                return True

        return False
