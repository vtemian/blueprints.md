"""Blueprints.md - Markdown-to-code generation system."""

__version__ = "0.1.0"

# Import unified classes
from .parser import Blueprint, Component, BlueprintReference, BlueprintParser
from .resolver import BlueprintResolver, ResolvedBlueprint
from .generator import CodeGenerator
from .natural_generator import NaturalCodeGenerator, UnifiedBlueprintSystem

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
