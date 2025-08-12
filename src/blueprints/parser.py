"""Claude-powered blueprint parser for intelligent understanding of natural language blueprints."""

import os
from pathlib import Path
from typing import Dict, List, Optional
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
    """Blueprint representation for natural language formats."""
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


class BlueprintParser:
    """Claude-powered blueprint parser for intelligent understanding of natural language blueprints."""
    
    def __init__(self):
        # Require ANTHROPIC_API_KEY
        if not os.getenv('ANTHROPIC_API_KEY'):
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for blueprint parsing. "
                "Set it with: export ANTHROPIC_API_KEY=your_key_here"
            )
        
        try:
            from .claude_parser import ClaudeBlueprintParser
            self.claude_parser = ClaudeBlueprintParser()
        except ImportError:
            raise ImportError(
                "anthropic package is required for blueprint parsing. "
                "Install it with: pip install anthropic"
            )
    
    def parse_file(self, file_path: Path) -> Blueprint:
        """Parse a blueprint file using Claude."""
        content = file_path.read_text()
        blueprint = self.parse_content(content)
        blueprint.file_path = file_path
        return blueprint
    
    def parse_content(self, content: str) -> Blueprint:
        """Parse blueprint content using Claude intelligence."""
        return self.claude_parser.parse_content(content)


# Legacy aliases for backward compatibility
CompactBlueprintParser = BlueprintParser
HybridBlueprintParser = BlueprintParser