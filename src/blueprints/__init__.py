"""Blueprints.md - Markdown-to-code generation system."""

__version__ = "0.1.0"

# Import unified classes
from .parser import Blueprint, Component, BlueprintReference, BlueprintParser
from .resolver import BlueprintResolver, ResolvedBlueprint
from .agentic_resolver import AgenticDependencyResolver, SmartBlueprintResolver
from .generator import CodeGenerator
from .natural_generator import NaturalCodeGenerator, UnifiedBlueprintSystem
from .factory import create_quality_enhanced_generator

__all__ = [
    "BlueprintParser",
    "Blueprint",
    "Component",
    "BlueprintReference",
    "CodeGenerator",
    "BlueprintResolver",
    "ResolvedBlueprint",
    "AgenticDependencyResolver",
    "SmartBlueprintResolver",
    "create_quality_enhanced_generator",
    "__version__",
]
