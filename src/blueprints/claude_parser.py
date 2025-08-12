"""Claude-based blueprint parser that uses AI to understand .md files."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from anthropic import Anthropic

# Import the existing data structures
from .parser import Blueprint, BlueprintReference, Method, Component
from .constants import DEFAULT_MODEL
from .logging_config import get_logger
from .utils import load_blueprint_spec, check_anthropic_api_key


class ClaudeBlueprintParser:
    """Claude-powered blueprint parser using BLUEPRINTS_SPEC.md as context."""

    def __init__(self):
        logger = get_logger('claude_parser')
        logger.debug("Initializing ClaudeBlueprintParser...")
        
        logger.debug("Checking API key...")
        check_anthropic_api_key("Claude-based parsing")
        logger.debug("API key check passed")
        
        logger.debug("Creating Anthropic client...")
        self.client = Anthropic()
        logger.debug("Anthropic client created")
        
        logger.debug("Loading blueprint specification...")
        self.blueprint_spec = load_blueprint_spec()
        logger.debug(f"Blueprint spec loaded ({len(self.blueprint_spec)} chars)")
        
        logger.debug("ClaudeBlueprintParser initialization complete")
    

    def parse_file(self, file_path: Path) -> Blueprint:
        """Parse a blueprint file using Claude."""
        content = file_path.read_text()
        blueprint = self.parse_content(content)
        blueprint.file_path = file_path
        return blueprint

    def parse_content(self, content: str) -> Blueprint:
        """Parse blueprint content using Claude."""
        logger = get_logger('claude_parser')
        logger.debug(f"Starting Claude parsing of {len(content)} character content")
        
        logger.debug("Calling Claude API for parsing...")
        parsed_data = self._parse_with_claude(content)
        logger.debug(f"Claude API returned data: {type(parsed_data)}")
        
        logger.debug("Converting parsed data to Blueprint object...")
        blueprint = self._convert_to_blueprint(parsed_data, content)
        logger.debug(f"Blueprint object created: {blueprint.module_name}")
        
        return blueprint

    def _parse_with_claude(self, content: str) -> dict:
        """Use Claude to parse blueprint content."""
        logger = get_logger('claude_parser')
        logger.debug("Building parsing prompt...")
        
        parsing_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

BLUEPRINT TO PARSE:
{content}

Parse this blueprint file and extract the following information in JSON format:
{{
    "module_name": "extracted module name from # header",
    "description": "main description of the module",
    "dependencies": [
        "list of external dependencies (libraries, packages)"
    ],
    "blueprint_references": [
        {{
            "module_path": "path like ../models/user or ./services/auth", 
            "items": ["list of specific items if mentioned"]
        }}
    ],
    "requirements": [
        "list of functional requirements"
    ],
    "sections": {{
        "section_name": ["list", "of", "items", "in", "section"]
    }},
    "components": [
        {{
            "type": "class/function/constant",
            "name": "component name",
            "methods": [
                {{
                    "name": "method name",
                    "params": "parameters",
                    "return_type": "return type if mentioned",
                    "is_async": true/false
                }}
            ]
        }}
    ]
}}

PARSING RULES:
1. Extract module name from the first # header
2. Get the main description (usually the first paragraph after the header)
3. Dependencies include both external packages AND @blueprint/references
4. Blueprint references are paths starting with @ like @../models/user
5. Requirements are functional/technical requirements listed
6. Components are specific classes, functions, or other code elements mentioned
7. Sections capture any additional structured information
8. If information is not present, use empty arrays/objects

Return ONLY the JSON, no explanations.
"""
        
        logger.debug(f"Making Claude API call (prompt: {len(parsing_prompt)} chars)...")
        response = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": parsing_prompt}]
        )
        logger.debug(f"Claude API response received ({len(response.content[0].text)} chars)")
        
        response_text = response.content[0].text
        logger.debug("Extracting JSON from Claude response...")
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            logger.debug("JSON pattern found, parsing...")
            parsed_json = json.loads(json_match.group())
            logger.debug(f"JSON parsed successfully: {list(parsed_json.keys())}")
            return parsed_json
        else:
            logger.error(f"Could not extract JSON from response: {response_text[:200]}...")
            raise ValueError("Could not extract JSON from Claude response")

    def _convert_to_blueprint(self, parsed_data: dict, raw_content: str) -> Blueprint:
        """Convert Claude's parsed data to Blueprint object."""
        # Extract blueprint references
        blueprint_refs = []
        for ref_data in parsed_data.get("blueprint_references", []):
            blueprint_refs.append(BlueprintReference(
                module_path=ref_data["module_path"],
                items=ref_data.get("items", [])
            ))
        
        # Extract components
        components = []
        for comp_data in parsed_data.get("components", []):
            methods = []
            for method_data in comp_data.get("methods", []):
                methods.append(Method(
                    name=method_data["name"],
                    params=method_data.get("params", ""),
                    return_type=method_data.get("return_type"),
                    is_async=method_data.get("is_async", False)
                ))
            
            components.append(Component(
                type=comp_data["type"],
                name=comp_data["name"],
                methods=methods
            ))
        
        return Blueprint(
            module_name=parsed_data.get("module_name", "unknown"),
            description=parsed_data.get("description", ""),
            blueprint_refs=blueprint_refs,
            components=components,
            dependencies=parsed_data.get("dependencies", []),
            requirements=parsed_data.get("requirements", []),
            sections=parsed_data.get("sections", {}),
            raw_content=raw_content
        )


# Legacy compatibility - keep the same interface
BlueprintParser = ClaudeBlueprintParser