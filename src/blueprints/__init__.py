"""Blueprints.md - Markdown-to-code generation system."""

__version__ = "0.1.0"

# Import original classes for backward compatibility
from .parser import Blueprint, Component, BlueprintReference
from .resolver import BlueprintResolver, ResolvedBlueprint

# Import the hybrid system as the default
from .natural_parser import HybridBlueprintParser
from .natural_generator import NaturalCodeGenerator, UnifiedBlueprintSystem

# Use hybrid system as defaults
BlueprintParser = HybridBlueprintParser
CodeGenerator = NaturalCodeGenerator

__all__ = [
    "BlueprintParser",
    "Blueprint",
    "Component",
    "BlueprintReference",
    "CodeGenerator",
    "BlueprintResolver",
    "ResolvedBlueprint",
    "__version__",
]
