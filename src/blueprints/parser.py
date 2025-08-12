"""Unified blueprint parser for both structured and natural language .md files."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class Method:
    """Represents a method or function signature."""

    name: str
    params: str
    return_type: Optional[str] = None
    comment: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class Component:
    """Represents a component (class, function, etc.) in a blueprint."""

    type: str  # "class", "function", "constant", "type_alias"
    name: str
    base_class: Optional[str] = None
    methods: List[Method] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    value: Optional[str] = None  # For constants and type aliases
    docstring: Optional[str] = None


@dataclass
class BlueprintReference:
    """Represents a reference to another blueprint."""

    module_path: str
    items: List[str] = field(default_factory=list)


@dataclass
class Blueprint:
    """Unified blueprint representation for both structured and natural formats."""

    module_name: str
    description: str = ""
    blueprint_refs: List[BlueprintReference] = field(default_factory=list)
    components: List[Component] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    raw_content: str = ""
    file_path: Optional[Path] = None
    
    # Natural language specific fields
    dependencies: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    sections: Dict[str, List[str]] = field(default_factory=dict)


def detect_blueprint_format(content: str) -> str:
    """Detect if content uses structured or natural language format.
    
    Returns:
        "structured" or "natural"
    """
    if not content.strip():
        return "natural"
    
    lines = content.strip().split("\n")
    
    # Look for structured format indicators in first 20 lines
    for line in lines[:20]:
        line_stripped = line.strip()
        
        if (
            line_stripped.startswith("deps:")
            or line_stripped.startswith("notes:")
            or re.match(r"^\w+\(.*\):$", line_stripped)  # Function signatures
            or re.match(r"^[A-Z_]+:", line_stripped)  # Constants
            or (line_stripped.startswith("- ") and ":" in line_stripped)  # Method signatures
        ):
            return "structured"
    
    return "natural"


def extract_module_name(content: str) -> str:
    """Extract module name from blueprint content."""
    lines = content.strip().split("\n")
    
    if not lines or not lines[0].startswith("#"):
        raise ValueError("Blueprint must start with # module.name")
    
    return lines[0].strip("#").strip()


def extract_description(content: str) -> str:
    """Extract description from blueprint content."""
    lines = content.strip().split("\n")
    
    if len(lines) < 2:
        return ""
    
    # For structured format, description is on line 2
    if detect_blueprint_format(content) == "structured":
        return lines[1].strip() if len(lines) > 1 else ""
    
    # For natural format, find first non-empty line after module name
    for i in range(1, len(lines)):
        line = lines[i].strip()
        if line and not line.startswith("#"):
            return line
    
    return ""


def parse_blueprint_refs(deps_str: str) -> List[BlueprintReference]:
    """Parse blueprint references from dependency string."""
    blueprint_refs = []
    
    # Split by semicolon for different dependencies
    for dep in deps_str.split(";"):
        dep = dep.strip()
        if not dep:
            continue
        
        # Only process blueprint references (starting with @ or .)
        if dep.startswith(".") or dep.startswith("@"):
            # Check if it has items in brackets
            if "[" in dep and "]" in dep:
                package = dep[:dep.index("[")].strip()
                items_str = dep[dep.index("[") + 1:dep.index("]")]
                items = [item.strip() for item in items_str.split(",")]
                
                # Remove @ prefix if present
                if package.startswith("@"):
                    package = package[1:]
                blueprint_refs.append(
                    BlueprintReference(module_path=package, items=items)
                )
            else:
                # Just a blueprint module name
                module = dep[1:] if dep.startswith("@") else dep
                blueprint_refs.append(BlueprintReference(module_path=module))
    
    return blueprint_refs


def parse_method_signature(line: str) -> Optional[Method]:
    """Parse a method signature line."""
    # Remove comments first
    comment = None
    if "#" in line:
        parts = line.split("#", 1)
        line = parts[0].strip()
        comment = parts[1].strip()
    
    # Check for property
    if ":" in line and "(" not in line:
        parts = line.split(":", 1)
        return Method(
            name=parts[0].strip(),
            params="",
            return_type=parts[1].strip(),
            comment=comment,
        )
    
    # Parse method signature
    match = re.match(r"^(?:async\s+)?(\w+)\((.*?)\)(?:\s*->\s*(.+))?$", line)
    if match:
        name, params, return_type = match.groups()
        return Method(
            name=name,
            params=params,
            return_type=return_type.strip() if return_type else None,
            comment=comment,
            is_async=line.strip().startswith("async "),
        )
    
    return None


def parse_structured_component(lines: List[str], start_idx: int) -> Optional[Component]:
    """Parse a component from structured format starting at given line."""
    line = lines[start_idx].strip()
    
    # Check for type alias (TypeName = ...)
    if "=" in line and not line.startswith("-"):
        parts = line.split("=", 1)
        if len(parts) == 2:
            name = parts[0].strip()
            value = parts[1].strip()
            return Component(type="type_alias", name=name, value=value)
    
    # Check for constant (CONSTANT_NAME: type = value)
    if re.match(r"^[A-Z_]+:", line):
        match = re.match(r"^([A-Z_]+):\s*([^=]+)(?:\s*=\s*(.+))?$", line)
        if match:
            name, type_str, value = match.groups()
            return Component(
                type="constant",
                name=name,
                properties={"type": type_str.strip()},
                value=value.strip() if value else None,
            )
    
    # Check for class definition
    class_match = re.match(r"^(\w+)(?:\(([^)]+)\))?:?\s*$", line)
    if (
        class_match
        and start_idx + 1 < len(lines)
        and lines[start_idx + 1].strip().startswith("-")
    ):
        name, base_class = class_match.groups()
        component = Component(type="class", name=name, base_class=base_class)
        
        # Parse class members
        i = start_idx + 1
        while i < len(lines) and (
            lines[i].strip().startswith("-")
            or lines[i].strip().startswith("@")
            or not lines[i].strip()
        ):
            member_line = lines[i].strip()
            if member_line.startswith("-"):
                method = parse_method_signature(member_line[1:].strip())
                if method:
                    component.methods.append(method)
            elif member_line.startswith("@"):
                # Handle decorator for next method
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("-"):
                    next_method = parse_method_signature(
                        lines[i + 1].strip()[1:].strip()
                    )
                    if next_method:
                        next_method.decorators.append(member_line)
                        component.methods.append(next_method)
                    i += 1  # Skip the next line since we processed it
            i += 1
        
        return component
    
    # Check for standalone function
    func_match = re.match(
        r"^(?:async\s+)?(\w+)\((.*?)\)(?:\s*->\s*(.+?))?:?\s*$", line
    )
    if func_match:
        is_async = line.strip().startswith("async ")
        name, params, return_type = func_match.groups()
        
        # Check for docstring
        docstring = None
        if start_idx + 1 < len(lines) and lines[start_idx + 1].strip().startswith('"""'):
            docstring = lines[start_idx + 1].strip().strip('"""')
        
        method = Method(
            name=name,
            params=params,
            return_type=return_type.strip() if return_type else None,
            is_async=is_async,
        )
        
        return Component(
            type="function", name=name, methods=[method], docstring=docstring
        )
    
    return None


def find_component_end(lines: List[str], start_idx: int) -> int:
    """Find where a component definition ends in structured format."""
    i = start_idx + 1
    while i < len(lines):
        line = lines[i].strip()
        # Component ends when we hit a new component, deps:, notes:, or empty line followed by non-indented content
        if (
            line.startswith("deps:")
            or line.startswith("notes:")
            or (
                line
                and not line.startswith("-")
                and not line.startswith("@")
                and not line.startswith('"""')
            )
        ):
            return i - 1
        i += 1
    return len(lines) - 1


def parse_structured_blueprint(content: str) -> Blueprint:
    """Parse structured format blueprint content."""
    lines = content.strip().split("\n")
    
    module_name = extract_module_name(content)
    description = extract_description(content)
    
    blueprint = Blueprint(
        module_name=module_name,
        description=description,
        raw_content=content
    )
    
    # Parse the rest of the content
    i = 2
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("deps:"):
            # Parse only blueprint references (ignore standard/3rd party deps)
            deps_str = line[5:].strip()
            refs = parse_blueprint_refs(deps_str)
            blueprint.blueprint_refs = refs
        
        elif line.startswith("notes:"):
            # Parse notes
            notes_str = line[6:].strip()
            blueprint.notes = [n.strip() for n in notes_str.split(",")]
        
        elif line and not line.startswith("#"):
            # Parse component
            component = parse_structured_component(lines, i)
            if component:
                blueprint.components.append(component)
                # Skip lines that belong to this component
                i = find_component_end(lines, i)
        
        i += 1
    
    return blueprint


def parse_natural_dependencies(blueprint: Blueprint, content: List[str]) -> None:
    """Parse dependencies section from natural language format."""
    for line in content:
        # Split by comma for multiple dependencies on one line
        deps = [dep.strip() for dep in line.split(",")]
        
        for dep in deps:
            if not dep:
                continue
            
            blueprint.dependencies.append(dep)
            
            # Check if it's a blueprint reference (starts with @ or relative path)
            if dep.startswith("@") or dep.startswith("./") or dep.startswith("../"):
                # Convert to BlueprintReference format
                clean_ref = dep.lstrip("@").lstrip("./").lstrip("../")
                if dep.startswith("@./"):
                    clean_ref = dep[3:]  # Remove @./
                elif dep.startswith("@../"):
                    clean_ref = ".." + dep[4:]  # Keep .. for parent directory
                elif dep.startswith("@"):
                    clean_ref = dep[1:]  # Remove @
                
                blueprint.blueprint_refs.append(BlueprintReference(module_path=clean_ref))


def save_natural_section(blueprint: Blueprint, section: Optional[str], content: List[str]) -> None:
    """Save a section from natural language format to blueprint."""
    if not section or not content:
        return
    
    if section == "dependencies":
        parse_natural_dependencies(blueprint, content)
    elif section == "requirements":
        blueprint.requirements = content
    else:
        # Store other sections as-is
        blueprint.sections[section] = content
        
        # Extract notes from sections containing "note"
        if "note" in section.lower():
            blueprint.notes.extend(content)


def parse_natural_blueprint(content: str) -> Blueprint:
    """Parse natural language format blueprint content."""
    lines = content.strip().split("\n")
    
    module_name = extract_module_name(content)
    description = extract_description(content)
    
    blueprint = Blueprint(
        module_name=module_name,
        description=description,
        raw_content=content
    )
    
    # Parse sections
    current_section = None
    current_content = []
    desc_start = 1
    
    # Find where description ends
    while desc_start < len(lines):
        line = lines[desc_start].strip()
        if line and not line.startswith("#"):
            desc_start += 1
            break
        desc_start += 1
    
    for i, line in enumerate(lines[desc_start:], desc_start):
        line_stripped = line.strip()
        
        # Detect section headers
        if line_stripped.lower().startswith("dependencies:"):
            save_natural_section(blueprint, current_section, current_content)
            current_section = "dependencies"
            current_content = []
            # Extract inline dependencies if present
            deps_inline = line_stripped[13:].strip()  # Remove "Dependencies:"
            if deps_inline:
                current_content.append(deps_inline)
        
        elif line_stripped.lower().startswith("requirements:"):
            save_natural_section(blueprint, current_section, current_content)
            current_section = "requirements"
            current_content = []
        
        elif re.match(r"^[A-Z][A-Za-z\s]+:", line_stripped):  # Generic section headers
            save_natural_section(blueprint, current_section, current_content)
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
    save_natural_section(blueprint, current_section, current_content)
    
    return blueprint


class BlueprintParser:
    """Unified parser that handles both structured and natural language blueprints."""
    
    def parse_file(self, file_path: Path) -> Blueprint:
        """Parse a blueprint file and return structured data."""
        content = file_path.read_text()
        blueprint = self.parse_content(content)
        blueprint.file_path = file_path
        return blueprint
    
    def parse_content(self, content: str) -> Blueprint:
        """Parse blueprint content, auto-detecting the format."""
        if detect_blueprint_format(content) == "structured":
            return parse_structured_blueprint(content)
        else:
            return parse_natural_blueprint(content)


# Legacy aliases for backward compatibility
CompactBlueprintParser = BlueprintParser
HybridBlueprintParser = BlueprintParser