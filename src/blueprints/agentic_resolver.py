"""Smart Dependency Resolution Agent using Claude for semantic understanding of blueprint dependencies."""

import json
from pathlib import Path
from typing import List, Optional, Set, Dict, Tuple
from dataclasses import dataclass, field

from anthropic import Anthropic

from .parser import Blueprint, BlueprintReference, BlueprintParser
from .constants import DEFAULT_MODEL
from .logging_config import get_logger
from .utils import check_anthropic_api_key
from .resolver import ResolvedBlueprint


@dataclass
class DependencyInsight:
    """Semantic understanding of a dependency relationship."""
    source_module: str
    target_module: str
    dependency_type: str  # "required", "optional", "circular", "inferred"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    suggested_path: Optional[str] = None
    missing: bool = False


@dataclass
class GenerationPlan:
    """Optimized plan for code generation order."""
    generation_order: List[Blueprint]
    complexity_scores: Dict[str, float]
    coupling_analysis: Dict[str, List[str]]
    circular_dependencies: List[Tuple[str, str]]
    resolution_strategies: List[str]


class SemanticDependencyAnalyzer:
    """Analyzes blueprint content to understand semantic dependencies beyond explicit references."""
    
    def __init__(self, client):
        self.client = client
        self._load_blueprint_spec()
    
    def _load_blueprint_spec(self):
        """Load BLUEPRINTS_SPEC.md for context."""
        spec_path = Path(__file__).parent.parent.parent / "BLUEPRINTS_SPEC.md"
        if spec_path.exists():
            self.blueprint_spec = spec_path.read_text()
        else:
            self.blueprint_spec = "Natural language blueprint format with @references"
    
    def analyze_dependencies(self, blueprint: Blueprint, project_context: str) -> List[DependencyInsight]:
        """Analyze blueprint content to understand all dependencies, including implicit ones."""
        analysis_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

PROJECT CONTEXT:
{project_context}

BLUEPRINT TO ANALYZE:
Module: {blueprint.module_name}
Content: {blueprint.raw_content}

EXISTING EXPLICIT REFERENCES:
{[ref.module_path for ref in blueprint.blueprint_refs]}

Analyze this blueprint and identify ALL dependencies - both explicit and implicit. Return JSON:

{{
    "dependencies": [
        {{
            "target_module": "module path/name",
            "dependency_type": "required|optional|inferred", 
            "confidence": 0.0-1.0,
            "reasoning": "why this dependency exists",
            "suggested_path": "suggested file path if inferable",
            "missing": true/false,
            "relationship": "uses|extends|implements|configures|calls"
        }}
    ],
    "missing_dependencies": [
        {{
            "suggested_module": "likely needed module",
            "reasoning": "why it's probably needed",
            "confidence": 0.0-1.0
        }}
    ]
}}

ANALYSIS RULES:
1. Look for implicit dependencies in requirements and descriptions
2. Identify missing dependencies based on mentioned functionality
3. Consider common patterns (models need databases, APIs need auth, etc.)
4. Assess confidence based on how explicit the dependency is
5. Include both technical and business logic dependencies

Return ONLY the JSON.
"""
        
        response = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        try:
            response_text = response.content[0].text
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                insights = []
                
                # Process dependencies
                for dep in data.get("dependencies", []):
                    insights.append(DependencyInsight(
                        source_module=blueprint.module_name,
                        target_module=dep["target_module"],
                        dependency_type=dep["dependency_type"],
                        confidence=dep["confidence"],
                        reasoning=dep["reasoning"],
                        suggested_path=dep.get("suggested_path"),
                        missing=dep.get("missing", False)
                    ))
                
                # Process missing dependencies
                for missing in data.get("missing_dependencies", []):
                    insights.append(DependencyInsight(
                        source_module=blueprint.module_name,
                        target_module=missing["suggested_module"],
                        dependency_type="inferred",
                        confidence=missing["confidence"],
                        reasoning=missing["reasoning"],
                        missing=True
                    ))
                
                return insights
            else:
                return []
        except Exception:
            # Fallback to empty analysis on parsing error
            return []


class IntelligentReferenceResolver:
    """Resolves ambiguous module references using project context and Claude intelligence."""
    
    def __init__(self, client, project_root: Path):
        self.client = client
        self.project_root = project_root
    
    def resolve_reference(self, ref: BlueprintReference, from_blueprint: Blueprint, 
                         available_modules: List[str]) -> Optional[str]:
        """Resolve ambiguous reference to actual file path using context."""
        resolution_prompt = f"""
PROJECT STRUCTURE: {available_modules}

REFERENCE TO RESOLVE: {ref.module_path}
FROM MODULE: {from_blueprint.module_name} 
FROM PATH: {from_blueprint.file_path}

CONTEXT:
Module Description: {from_blueprint.description}
Module Requirements: {from_blueprint.requirements}

Given the reference "{ref.module_path}" from "{from_blueprint.module_name}", determine the most likely actual file path.

Consider:
1. Relative path resolution (../, ./, etc.)
2. Common naming conventions
3. Project structure patterns
4. Context clues from the blueprint content

Return JSON:
{{
    "resolved_path": "most likely file path",
    "confidence": 0.0-1.0,
    "reasoning": "explanation of resolution logic",
    "alternatives": ["other possible paths"]
}}

Return ONLY the JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": resolution_prompt}]
            )
            
            response_text = response.content[0].text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("resolved_path")
            
        except Exception:
            pass
        
        # Fallback to simple resolution
        return self._fallback_resolve(ref, from_blueprint)
    
    def _fallback_resolve(self, ref: BlueprintReference, from_blueprint: Blueprint) -> Optional[str]:
        """Simple resolution for cases where Claude analysis fails."""
        return ref.module_path


class OptimalGenerationPlanner:
    """Determines optimal order for code generation based on complexity and coupling."""
    
    def __init__(self, client):
        self.client = client
    
    def create_generation_plan(self, blueprints: List[Blueprint], 
                              dependencies: Dict[str, List[DependencyInsight]]) -> GenerationPlan:
        """Create optimal generation plan using Claude analysis."""
        blueprint_summaries = []
        for bp in blueprints:
            blueprint_summaries.append(f"- {bp.module_name}: {bp.description}")
        
        planning_prompt = f"""
BLUEPRINTS TO GENERATE:
{chr(10).join(blueprint_summaries)}

DEPENDENCY RELATIONSHIPS:
{self._format_dependencies(dependencies)}

Create an optimal generation plan considering:
1. Dependency order (dependencies first)
2. Complexity levels (simple to complex)
3. Coupling analysis (loosely coupled first)
4. Circular dependency resolution

Return JSON:
{{
    "generation_order": ["ordered", "list", "of", "module.names"],
    "complexity_scores": {{
        "module.name": 0.0-1.0
    }},
    "coupling_analysis": {{
        "module.name": ["modules", "it", "couples", "with"]
    }},
    "circular_dependencies": [["module1", "module2"]],
    "resolution_strategies": [
        "strategy for handling circular deps",
        "other optimization strategies"
    ]
}}

PLANNING PRINCIPLES:
1. Generate foundation modules (models, core) first
2. Then services and business logic
3. Finally UI and integration layers
4. Break circular dependencies with interfaces/abstractions
5. Consider complexity - simple modules enable complex ones

Return ONLY the JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": planning_prompt}]
            )
            
            response_text = response.content[0].text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Map module names back to blueprints
                name_to_blueprint = {bp.module_name: bp for bp in blueprints}
                ordered_blueprints = []
                for name in data.get("generation_order", []):
                    if name in name_to_blueprint:
                        ordered_blueprints.append(name_to_blueprint[name])
                
                return GenerationPlan(
                    generation_order=ordered_blueprints,
                    complexity_scores=data.get("complexity_scores", {}),
                    coupling_analysis=data.get("coupling_analysis", {}),
                    circular_dependencies=data.get("circular_dependencies", []),
                    resolution_strategies=data.get("resolution_strategies", [])
                )
        except Exception:
            pass
        
        # Fallback to simple order
        return GenerationPlan(
            generation_order=blueprints,
            complexity_scores={},
            coupling_analysis={},
            circular_dependencies=[],
            resolution_strategies=[]
        )
    
    def _format_dependencies(self, dependencies: Dict[str, List[DependencyInsight]]) -> str:
        """Format dependencies for the prompt."""
        lines = []
        for source, deps in dependencies.items():
            dep_list = [f"{d.target_module} ({d.dependency_type})" for d in deps]
            lines.append(f"{source}: {', '.join(dep_list)}")
        return "\n".join(lines)


class AgenticDependencyResolver:
    """Smart dependency resolver using Claude for semantic understanding."""
    
    def __init__(self, project_root: Optional[Path] = None):
        logger = get_logger('agentic_resolver')
        logger.debug("Initializing AgenticDependencyResolver...")
        
        self.project_root = project_root or Path.cwd()
        logger.debug(f"Project root: {self.project_root}")
        
        logger.debug("Creating blueprint parser...")
        self.parser = BlueprintParser()
        logger.debug("Blueprint parser created")
        
        # Initialize Claude client
        logger.debug("Checking API key...")
        check_anthropic_api_key("agentic dependency resolution")
        logger.debug("API key check passed")
        
        logger.debug("Creating Anthropic client...")
        self.client = Anthropic()
        logger.debug("Anthropic client created")
        
        # Initialize components
        logger.debug("Initializing semantic analyzer...")
        self.semantic_analyzer = SemanticDependencyAnalyzer(self.client)
        logger.debug("Semantic analyzer created")
        
        logger.debug("Initializing reference resolver...")
        self.reference_resolver = IntelligentReferenceResolver(self.client, self.project_root)
        logger.debug("Reference resolver created")
        
        logger.debug("Initializing generation planner...")
        self.generation_planner = OptimalGenerationPlanner(self.client)
        logger.debug("Generation planner created")
        
        # Add performance optimizations
        self._semantic_cache = {}  # Cache semantic analysis results
        self._fast_mode = True  # Skip semantic analysis when explicit refs exist
        
        logger.debug("AgenticDependencyResolver initialization complete")
        # Pure Claude system - no fallbacks
    
    def resolve(self, blueprint_path: Path) -> ResolvedBlueprint:
        """Resolve blueprint dependencies using Claude-powered semantic understanding."""
        logger = get_logger('agentic_resolver')
        logger.info(f"Starting intelligent dependency resolution for: {blueprint_path}")
        
        result = self._intelligent_resolve(blueprint_path)
        logger.info("Intelligent dependency resolution completed successfully")
        return result
    
    def _intelligent_resolve(self, blueprint_path: Path) -> ResolvedBlueprint:
        """Perform intelligent resolution using Claude."""
        logger = get_logger('agentic_resolver')
        logger.info("Starting intelligent resolution process...")
        
        logger.debug(f"Parsing main blueprint: {blueprint_path}")
        main_blueprint = self.parser.parse_file(blueprint_path)
        logger.info(f"Main blueprint parsed: {main_blueprint.module_name}")
        logger.debug(f"Main blueprint has {len(main_blueprint.blueprint_refs)} explicit references")
        
        # Build project context
        logger.debug("Building project context...")
        project_context = self._build_project_context()
        logger.debug(f"Project context built ({len(project_context)} characters)")
        
        # Discover all dependencies using semantic analysis
        logger.info("Starting recursive dependency discovery...")
        all_blueprints = {}
        all_dependencies = {}
        visited = set()
        
        self._discover_dependencies_recursive(
            main_blueprint, all_blueprints, all_dependencies, visited, project_context
        )
        
        logger.info(f"Dependency discovery completed! Found {len(all_blueprints)} total blueprints:")
        for name in all_blueprints.keys():
            logger.info(f"  - {name}")
        
        # Create optimal generation plan
        blueprint_list = list(all_blueprints.values())
        logger.debug(f"Creating generation plan for {len(blueprint_list)} blueprints...")
        generation_plan = self.generation_planner.create_generation_plan(
            blueprint_list, all_dependencies
        )
        logger.debug("Generation plan created")
        
        # Return resolved blueprint with intelligent ordering
        dependencies = [bp for bp in generation_plan.generation_order if bp != main_blueprint]
        logger.info(f"Final resolution: main + {len(dependencies)} dependencies = {len(dependencies) + 1} total files to generate")
        
        resolved = ResolvedBlueprint(
            main=main_blueprint,
            dependencies=dependencies,
            generation_order=generation_plan.generation_order,
            complexity_scores=generation_plan.complexity_scores,
            coupling_analysis=generation_plan.coupling_analysis,
            circular_dependencies=generation_plan.circular_dependencies,
            resolution_strategies=generation_plan.resolution_strategies
        )
        
        logger.info("Intelligent resolution completed successfully")
        return resolved
    
    def _discover_dependencies_recursive(self, blueprint: Blueprint, all_blueprints: Dict[str, Blueprint], 
                                       all_dependencies: Dict[str, List[DependencyInsight]], 
                                       visited: Set[str], project_context: str):
        """Recursively discover dependencies using semantic analysis."""
        logger = get_logger('agentic_resolver')
        logger.debug(f"[RECURSIVE] Processing blueprint: {blueprint.module_name}")
        logger.debug(f"[RECURSIVE] Already visited: {list(visited)}")
        
        if blueprint.module_name in visited:
            logger.debug(f"[RECURSIVE] Skipping {blueprint.module_name} - already visited")
            return
        
        logger.debug(f"[RECURSIVE] Adding {blueprint.module_name} to visited set")
        visited.add(blueprint.module_name)
        all_blueprints[blueprint.module_name] = blueprint
        logger.debug(f"[RECURSIVE] Total blueprints discovered so far: {len(all_blueprints)}")
        
        # First, process explicit blueprint references
        logger.debug(f"[RECURSIVE] Processing {len(blueprint.blueprint_refs)} explicit blueprint references...")
        for i, ref in enumerate(blueprint.blueprint_refs, 1):
            logger.debug(f"[RECURSIVE] [{i}/{len(blueprint.blueprint_refs)}] Processing reference: {ref.module_path}")
            
            # Try to load the reference directly
            dep_blueprint = self._load_blueprint_reference(ref, blueprint)
            if dep_blueprint:
                logger.debug(f"[RECURSIVE] Successfully loaded referenced blueprint: {dep_blueprint.module_name}")
                if dep_blueprint.module_name not in visited:
                    logger.debug(f"[RECURSIVE] Recursing into referenced blueprint: {dep_blueprint.module_name}")
                    self._discover_dependencies_recursive(
                        dep_blueprint, all_blueprints, all_dependencies, visited, project_context
                    )
                else:
                    logger.debug(f"[RECURSIVE] Referenced blueprint {dep_blueprint.module_name} already processed")
            else:
                logger.warning(f"[RECURSIVE] Failed to load referenced blueprint: {ref.module_path}")
        
        # Skip semantic analysis in fast mode when explicit references exist
        if self._fast_mode and len(blueprint.blueprint_refs) > 0:
            logger.debug(f"[RECURSIVE] Fast mode: skipping semantic analysis for {blueprint.module_name} (has {len(blueprint.blueprint_refs)} explicit refs)")
            insights = []
        else:
            # Get semantic insights about additional dependencies (with caching)
            logger.debug(f"[RECURSIVE] Performing semantic analysis for {blueprint.module_name}...")
            cache_key = f"{blueprint.module_name}_{hash(blueprint.raw_content)}"
            
            if cache_key in self._semantic_cache:
                logger.debug(f"[RECURSIVE] Using cached semantic analysis for {blueprint.module_name}")
                insights = self._semantic_cache[cache_key]
            else:
                logger.debug(f"[RECURSIVE] Running semantic analysis for {blueprint.module_name}")
                insights = self.semantic_analyzer.analyze_dependencies(blueprint, project_context)
                self._semantic_cache[cache_key] = insights
            
        all_dependencies[blueprint.module_name] = insights
        logger.debug(f"[RECURSIVE] Semantic analysis found {len(insights)} dependency insights")
        
        # Process semantic insights
        for i, insight in enumerate(insights, 1):
            logger.debug(f"[RECURSIVE] [{i}/{len(insights)}] Processing semantic insight: {insight.target_module} ({insight.dependency_type})")
            
            if insight.missing:
                logger.debug(f"[RECURSIVE] Skipping missing dependency: {insight.target_module}")
                continue
            
            # Try to resolve and load the dependency
            dep_blueprint = self._load_dependency(insight, blueprint)
            if dep_blueprint:
                logger.debug(f"[RECURSIVE] Successfully loaded semantic dependency: {dep_blueprint.module_name}")
                if dep_blueprint.module_name not in visited:
                    logger.debug(f"[RECURSIVE] Recursing into semantic dependency: {dep_blueprint.module_name}")
                    self._discover_dependencies_recursive(
                        dep_blueprint, all_blueprints, all_dependencies, visited, project_context
                    )
                else:
                    logger.debug(f"[RECURSIVE] Semantic dependency {dep_blueprint.module_name} already processed")
            else:
                logger.debug(f"[RECURSIVE] Failed to load semantic dependency: {insight.target_module}")
        
        logger.debug(f"[RECURSIVE] Completed processing {blueprint.module_name}. Total blueprints: {len(all_blueprints)}")
    
    def _load_blueprint_reference(self, ref: BlueprintReference, from_blueprint: Blueprint) -> Optional[Blueprint]:
        """Load a blueprint directly from a blueprint reference."""
        logger = get_logger('agentic_resolver')
        logger.debug(f"[LOAD_REF] Loading reference {ref.module_path} from {from_blueprint.module_name}")
        
        # Try to find the blueprint file directly
        blueprint_file = self._find_blueprint_file(ref.module_path)
        if blueprint_file and blueprint_file.exists():
            logger.debug(f"[LOAD_REF] Found blueprint file: {blueprint_file}")
            try:
                blueprint = self.parser.parse_file(blueprint_file)
                logger.debug(f"[LOAD_REF] Successfully parsed blueprint: {blueprint.module_name}")
                return blueprint
            except Exception as e:
                logger.warning(f"[LOAD_REF] Failed to parse blueprint {blueprint_file}: {e}")
        else:
            logger.warning(f"[LOAD_REF] Blueprint file not found for reference: {ref.module_path}")
        
        return None
    
    def _load_dependency(self, insight: DependencyInsight, from_blueprint: Blueprint) -> Optional[Blueprint]:
        """Load a dependency blueprint based on semantic insight."""
        logger = get_logger('agentic_resolver')
        logger.debug(f"[LOAD_DEP] Loading dependency {insight.target_module} from {from_blueprint.module_name}")
        
        # For semantic insights, use direct path resolution instead of the intelligent resolver
        # to avoid the complex path resolution issues
        blueprint_file = self._find_blueprint_file(insight.target_module)
        
        if blueprint_file and blueprint_file.exists():
            logger.debug(f"[LOAD_DEP] Found blueprint file: {blueprint_file}")
            try:
                blueprint = self.parser.parse_file(blueprint_file)
                logger.debug(f"[LOAD_DEP] Successfully parsed dependency: {blueprint.module_name}")
                return blueprint
            except Exception as e:
                logger.warning(f"[LOAD_DEP] Failed to parse blueprint {blueprint_file}: {e}")
        else:
            logger.debug(f"[LOAD_DEP] Blueprint file not found for: {insight.target_module}")
        
        return None
    
    def _build_project_context(self) -> str:
        """Build context about the project structure for semantic analysis."""
        context_parts = []
        
        # Add project structure
        available_modules = self._get_available_modules()
        if available_modules:
            context_parts.append("AVAILABLE BLUEPRINT MODULES:")
            context_parts.extend(f"- {module}" for module in available_modules[:20])  # Limit for token efficiency
        
        return "\n".join(context_parts)
    
    def _get_available_modules(self) -> List[str]:
        """Get list of available blueprint modules in the project."""
        modules = []
        for md_file in self.project_root.rglob("*.md"):
            if md_file.name != "README.md" and not md_file.name.startswith("."):
                # Convert file path to module name
                relative_path = md_file.relative_to(self.project_root)
                module_name = str(relative_path.with_suffix("")).replace("/", ".")
                modules.append(module_name)
        return modules
    
    def _find_blueprint_file(self, module_path: str) -> Optional[Path]:
        """Find blueprint file by module path."""
        logger = get_logger('agentic_resolver')
        logger.debug(f"[FIND_FILE] Searching for blueprint file: {module_path}")
        
        # Clean up the module path - remove @ prefix and handle relative paths
        clean_path = module_path
        if clean_path.startswith("@"):
            clean_path = clean_path[1:]  # Remove @
            logger.debug(f"[FIND_FILE] Removed @ prefix: {clean_path}")
        
        # Handle relative paths starting with ./
        if clean_path.startswith("./"):
            clean_path = clean_path[2:]  # Remove ./
            logger.debug(f"[FIND_FILE] Removed ./ prefix: {clean_path}")
        
        # Handle relative paths starting with ../
        elif clean_path.startswith("../"):
            clean_path = clean_path[3:]  # Remove ../
            logger.debug(f"[FIND_FILE] Removed ../ prefix: {clean_path}")
        
        # Handle both dot-separated and slash-separated paths
        if "." in clean_path:
            slash_path = "/".join(clean_path.split("."))
        else:
            slash_path = clean_path
        
        # Try common patterns relative to project root (examples/task_api)
        candidates = [
            self.project_root / f"{slash_path}.md",
            self.project_root / f"{clean_path}.md", 
            self.project_root / slash_path / f"{Path(slash_path).name}.md",
        ]
        
        logger.debug(f"[FIND_FILE] Trying candidates:")
        for candidate in candidates:
            logger.debug(f"[FIND_FILE]   - {candidate}")
            if candidate.exists():
                logger.debug(f"[FIND_FILE] ✓ Found: {candidate}")
                return candidate
        
        logger.debug(f"[FIND_FILE] ✗ No blueprint file found for: {module_path}")
        return None
    
    # Maintain compatibility with existing interface
    def get_context_for_generation(self, resolved: ResolvedBlueprint) -> str:
        """Create context string for code generation using Claude intelligence."""
        context_parts = []
        
        # Add dependencies first
        if resolved.dependencies:
            context_parts.append("=== REFERENCED BLUEPRINTS ===")
            for dep in resolved.dependencies:
                context_parts.append(f"--- {dep.module_name} ---")
                context_parts.append(dep.raw_content.strip())
                context_parts.append("")
        
        # Add main blueprint
        context_parts.append("=== MAIN BLUEPRINT TO IMPLEMENT ===")
        context_parts.append(resolved.main.raw_content.strip())
        
        return "\n".join(context_parts)
    
    def get_dependencies_for_blueprint(self, blueprint: Blueprint, resolved: ResolvedBlueprint) -> List[Blueprint]:
        """Get direct dependencies for a blueprint using semantic analysis."""
        dependencies = []
        
        # Find blueprints that this blueprint directly references
        for ref in blueprint.blueprint_refs:
            for dep in resolved.dependencies:
                if dep.module_name == ref.module_path or dep.file_path and dep.file_path.stem == ref.module_path.split('.')[-1]:
                    dependencies.append(dep)
        
        return dependencies


# Maintain compatibility - this can replace BlueprintResolver
class SmartBlueprintResolver(AgenticDependencyResolver):
    """Alias for backwards compatibility."""
    pass