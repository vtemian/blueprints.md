"""Claude-powered blueprint parser for intelligent understanding of natural language blueprints."""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .logging_config import get_logger
from .utils import check_anthropic_api_key


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
        logger = get_logger('parser')
        logger.debug("Initializing BlueprintParser...")
        
        logger.debug("Checking API key...")
        check_anthropic_api_key("blueprint parsing")
        logger.debug("API key validation passed")
        
        try:
            logger.debug("Importing ClaudeBlueprintParser...")
            from .claude_parser import ClaudeBlueprintParser
            logger.debug("Creating ClaudeBlueprintParser instance...")
            self.claude_parser = ClaudeBlueprintParser()
            logger.debug("ClaudeBlueprintParser initialized successfully")
        except ImportError as e:
            logger.error(f"Import error: {e}")
            raise ImportError(
                "anthropic package is required for blueprint parsing. "
                "Install it with: pip install anthropic"
            )
        except Exception as e:
            logger.error(f"Unexpected error initializing parser: {e}")
            raise
    
    def parse_file(self, file_path: Path) -> Blueprint:
        """Parse a blueprint file using Claude."""
        logger = get_logger('parser')
        logger.info(f"Parsing blueprint file: {file_path}")
        logger.debug(f"File exists: {file_path.exists()}")
        
        try:
            logger.debug(f"Reading file content...")
            content = file_path.read_text()
            logger.debug(f"File content length: {len(content)} characters")
            
            logger.debug("Calling parse_content...")
            blueprint = self.parse_content(content)
            blueprint.file_path = file_path
            
            logger.info(f"Successfully parsed blueprint: {blueprint.module_name}")
            logger.debug(f"Blueprint has {len(blueprint.blueprint_refs)} references")
            return blueprint
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            raise
    
    def parse_content(self, content: str) -> Blueprint:
        """Parse blueprint content using Claude intelligence."""
        logger = get_logger('parser')
        logger.debug(f"Parsing content ({len(content)} chars)...")
        
        try:
            result = self.claude_parser.parse_content(content)
            logger.debug(f"Content parsed successfully, module: {result.module_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to parse content: {e}")
            raise


# Legacy aliases for backward compatibility
CompactBlueprintParser = BlueprintParser
HybridBlueprintParser = BlueprintParser