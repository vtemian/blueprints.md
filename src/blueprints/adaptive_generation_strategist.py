"""Adaptive generation strategies using single Claude agent for intelligent code generation decisions."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from anthropic import Anthropic

from .parser import Blueprint
from .constants import DEFAULT_MODEL
from .utils import check_anthropic_api_key


class ArchitecturalPattern(Enum):
    """Different architectural patterns Claude can choose from."""
    FUNCTIONAL = "functional"
    OBJECT_ORIENTED = "object_oriented"
    PROCEDURAL = "procedural"
    REACTIVE = "reactive"
    LAYERED = "layered"
    MICROSERVICE = "microservice"


class ComplexityLevel(Enum):
    """Complexity levels for code generation."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    ROBUST = "robust"
    ENTERPRISE = "enterprise"


class TechnologyApproach(Enum):
    """Technology approach preferences."""
    MODERN = "modern"
    STABLE = "stable"
    PERFORMANCE = "performance"
    SIMPLICITY = "simplicity"


@dataclass
class GenerationStrategy:
    """Complete strategy for code generation."""
    architectural_pattern: ArchitecturalPattern
    complexity_level: ComplexityLevel
    technology_approach: TechnologyApproach
    specific_frameworks: List[str] = field(default_factory=list)
    coding_patterns: List[str] = field(default_factory=list)
    optimization_focus: List[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.8


@dataclass
class ProjectContext:
    """Context about the project for strategy selection."""
    project_size: str  # "small", "medium", "large"
    domain: str  # "web_api", "data_processing", "ml", "cli", etc.
    existing_patterns: List[str] = field(default_factory=list)
    performance_requirements: str = "standard"  # "low", "standard", "high", "critical"
    team_experience: str = "intermediate"  # "beginner", "intermediate", "expert"
    deployment_target: str = "cloud"  # "cloud", "on_premise", "edge", "mobile"
    maintenance_priority: str = "medium"  # "low", "medium", "high"


class AdaptiveGenerationStrategist:
    """Single Claude agent that chooses optimal generation strategies based on context."""
    
    def __init__(self):
        check_anthropic_api_key("adaptive generation strategies")
        
        
        self.client = Anthropic()
        
        self._load_blueprint_spec()
    
    def _load_blueprint_spec(self):
        """Load blueprint specification for context."""
        spec_path = Path(__file__).parent.parent.parent / "BLUEPRINTS_SPEC.md"
        if spec_path.exists():
            self.blueprint_spec = spec_path.read_text()
        else:
            self.blueprint_spec = "Natural language blueprint format"
    
    def analyze_project_context(self, blueprint: Blueprint, 
                               available_modules: List[str] = None) -> ProjectContext:
        """Analyze project to understand context for strategy selection."""
        
        modules_context = ""
        if available_modules:
            modules_context = f"Available project modules: {', '.join(available_modules[:10])}"
        
        context_analysis_prompt = f"""
BLUEPRINT TO ANALYZE:
Module: {blueprint.module_name}
Description: {blueprint.description}
Content: {blueprint.raw_content[:1000]}

{modules_context}

Analyze this blueprint and project context to determine:

1. PROJECT SIZE: How large is this project?
   - "small": Single module/script, simple functionality
   - "medium": Multiple modules, moderate complexity
   - "large": Complex system with many interconnected modules

2. DOMAIN: What type of application/system is this?
   - "web_api": REST/GraphQL APIs, web services
   - "data_processing": ETL, analytics, data pipelines
   - "ml": Machine learning, AI applications
   - "cli": Command line tools, scripts
   - "desktop_app": GUI applications
   - "mobile_backend": Mobile app backends
   - "enterprise": Enterprise systems, ERP
   - "embedded": IoT, embedded systems
   - "other": Specify the domain

3. PERFORMANCE REQUIREMENTS: What are the performance needs?
   - "low": Simple scripts, internal tools
   - "standard": Typical business applications
   - "high": High-traffic services, real-time processing
   - "critical": Financial systems, safety-critical applications

4. EXISTING PATTERNS: What patterns are already in use? (infer from modules/description)

5. DEPLOYMENT TARGET: Where will this run?
   - "cloud": AWS/GCP/Azure cloud platforms
   - "on_premise": Company servers
   - "edge": Edge computing
   - "mobile": Mobile devices
   - "desktop": Desktop computers

Return JSON:
{{
    "project_size": "small|medium|large",
    "domain": "web_api|data_processing|ml|cli|desktop_app|mobile_backend|enterprise|embedded|other",
    "performance_requirements": "low|standard|high|critical",
    "existing_patterns": ["pattern1", "pattern2"],
    "deployment_target": "cloud|on_premise|edge|mobile|desktop",
    "maintenance_priority": "low|medium|high",
    "team_experience": "intermediate",
    "reasoning": "explanation of the analysis"
}}

Return ONLY the JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": context_analysis_prompt}]
            )
            
            response_text = response.content[0].text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return ProjectContext(
                    project_size=data.get("project_size", "medium"),
                    domain=data.get("domain", "web_api"),
                    existing_patterns=data.get("existing_patterns", []),
                    performance_requirements=data.get("performance_requirements", "standard"),
                    team_experience=data.get("team_experience", "intermediate"),
                    deployment_target=data.get("deployment_target", "cloud"),
                    maintenance_priority=data.get("maintenance_priority", "medium")
                )
                
        except Exception:
            pass
        
        # Fallback context analysis
        return self._fallback_context_analysis(blueprint)
    
    def _fallback_context_analysis(self, blueprint: Blueprint) -> ProjectContext:
        """Fallback context analysis using heuristics."""
        # Simple heuristics based on content
        content_lower = blueprint.raw_content.lower()
        
        # Determine domain
        domain = "web_api"
        if "fastapi" in content_lower or "flask" in content_lower or "api" in content_lower:
            domain = "web_api"
        elif "pandas" in content_lower or "numpy" in content_lower or "data" in content_lower:
            domain = "data_processing"
        elif "click" in content_lower or "argparse" in content_lower or "cli" in content_lower:
            domain = "cli"
        elif "ml" in content_lower or "sklearn" in content_lower or "tensorflow" in content_lower:
            domain = "ml"
        
        # Determine size based on content length and complexity
        project_size = "small"
        if len(blueprint.raw_content) > 500:
            project_size = "medium"
        if len(blueprint.raw_content) > 1000:
            project_size = "large"
        
        return ProjectContext(
            project_size=project_size,
            domain=domain,
            performance_requirements="standard",
            deployment_target="cloud"
        )
    
    def select_optimal_strategy(self, blueprint: Blueprint, 
                               project_context: ProjectContext,
                               language: str = "python") -> GenerationStrategy:
        """Select optimal generation strategy based on blueprint and context."""
        
        strategy_selection_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

BLUEPRINT TO GENERATE:
Module: {blueprint.module_name}
Description: {blueprint.description}
Content: {blueprint.raw_content[:1200]}

PROJECT CONTEXT:
- Size: {project_context.project_size}
- Domain: {project_context.domain}
- Performance needs: {project_context.performance_requirements}
- Deployment: {project_context.deployment_target}
- Maintenance priority: {project_context.maintenance_priority}
- Team experience: {project_context.team_experience}
- Existing patterns: {project_context.existing_patterns}

TARGET LANGUAGE: {language}

Select the optimal generation strategy for this specific blueprint and context.

Consider:
1. ARCHITECTURAL PATTERN - What's the best approach?
   - functional: Pure functions, immutable data, functional composition
   - object_oriented: Classes, inheritance, encapsulation, polymorphism
   - procedural: Sequential steps, simple functions, minimal state
   - reactive: Event-driven, streams, reactive programming
   - layered: Clear separation of concerns, layered architecture
   - microservice: Service-oriented, distributed, independent deployment

2. COMPLEXITY LEVEL - How robust should the implementation be?
   - minimal: Basic implementation, minimal error handling
   - standard: Good practices, reasonable error handling
   - robust: Comprehensive error handling, validation, logging
   - enterprise: Full enterprise patterns, monitoring, resilience

3. TECHNOLOGY APPROACH - What philosophy to follow?
   - modern: Latest features, cutting-edge libraries
   - stable: Proven technologies, long-term support
   - performance: Speed optimized, efficient algorithms
   - simplicity: Easy to understand and maintain

4. SPECIFIC FRAMEWORKS/LIBRARIES - What to use?
5. CODING PATTERNS - What patterns to apply?
6. OPTIMIZATION FOCUS - What to optimize for?

Return JSON:
{{
    "architectural_pattern": "functional|object_oriented|procedural|reactive|layered|microservice",
    "complexity_level": "minimal|standard|robust|enterprise",
    "technology_approach": "modern|stable|performance|simplicity",
    "specific_frameworks": ["framework1", "framework2"],
    "coding_patterns": ["pattern1", "pattern2"],
    "optimization_focus": ["readability", "performance", "maintainability"],
    "reasoning": "detailed explanation of why this strategy is optimal",
    "confidence": 0.0-1.0
}}

Be specific and practical. Consider the actual requirements and constraints.

Return ONLY the JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": strategy_selection_prompt}]
            )
            
            response_text = response.content[0].text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return GenerationStrategy(
                    architectural_pattern=ArchitecturalPattern(data.get("architectural_pattern", "object_oriented")),
                    complexity_level=ComplexityLevel(data.get("complexity_level", "standard")),
                    technology_approach=TechnologyApproach(data.get("technology_approach", "stable")),
                    specific_frameworks=data.get("specific_frameworks", []),
                    coding_patterns=data.get("coding_patterns", []),
                    optimization_focus=data.get("optimization_focus", ["readability"]),
                    reasoning=data.get("reasoning", "Strategy selected based on context analysis"),
                    confidence=data.get("confidence", 0.8)
                )
                
        except Exception:
            pass
        
        # Fallback strategy selection
        return self._fallback_strategy_selection(project_context, language)
    
    def _fallback_strategy_selection(self, context: ProjectContext, language: str) -> GenerationStrategy:
        """Fallback strategy selection using heuristics."""
        # Simple heuristic-based strategy selection
        
        # Choose architectural pattern based on domain
        pattern = ArchitecturalPattern.OBJECT_ORIENTED
        if context.domain in ["data_processing", "ml"]:
            pattern = ArchitecturalPattern.FUNCTIONAL
        elif context.domain == "cli":
            pattern = ArchitecturalPattern.PROCEDURAL
        elif context.domain == "web_api":
            pattern = ArchitecturalPattern.LAYERED
        
        # Choose complexity based on project size and performance needs
        complexity = ComplexityLevel.STANDARD
        if context.project_size == "large" or context.performance_requirements in ["high", "critical"]:
            complexity = ComplexityLevel.ROBUST
        elif context.project_size == "small":
            complexity = ComplexityLevel.MINIMAL
        
        # Choose technology approach
        tech_approach = TechnologyApproach.STABLE
        if context.performance_requirements in ["high", "critical"]:
            tech_approach = TechnologyApproach.PERFORMANCE
        elif context.team_experience == "beginner":
            tech_approach = TechnologyApproach.SIMPLICITY
        
        return GenerationStrategy(
            architectural_pattern=pattern,
            complexity_level=complexity,
            technology_approach=tech_approach,
            optimization_focus=["readability", "maintainability"],
            reasoning="Fallback strategy based on heuristics",
            confidence=0.6
        )
    
    def enhance_prompt_with_strategy(self, base_prompt: str, 
                                   strategy: GenerationStrategy,
                                   language: str) -> str:
        """Enhance the generation prompt with strategic guidance."""
        
        strategy_guidance = f"""
GENERATION STRATEGY (Selected for optimal results):

ARCHITECTURAL APPROACH: {strategy.architectural_pattern.value}
{self._get_architectural_guidance(strategy.architectural_pattern)}

COMPLEXITY LEVEL: {strategy.complexity_level.value}
{self._get_complexity_guidance(strategy.complexity_level)}

TECHNOLOGY APPROACH: {strategy.technology_approach.value}
{self._get_technology_guidance(strategy.technology_approach)}

SPECIFIC FRAMEWORKS/LIBRARIES:
{chr(10).join(f"- {fw}" for fw in strategy.specific_frameworks) if strategy.specific_frameworks else "- Use standard library when possible"}

CODING PATTERNS TO APPLY:
{chr(10).join(f"- {pattern}" for pattern in strategy.coding_patterns) if strategy.coding_patterns else "- Follow standard patterns for the chosen architecture"}

OPTIMIZATION PRIORITIES:
{chr(10).join(f"- {focus}" for focus in strategy.optimization_focus)}

STRATEGY REASONING: {strategy.reasoning}

IMPLEMENTATION GUIDELINES:
Apply the above strategy consistently throughout the code. The architectural pattern should be evident in the code structure, the complexity level should match the robustness of error handling and validation, and the technology approach should guide library and feature choices.

"""
        
        # Insert strategy guidance into the base prompt
        enhanced_prompt = f"{strategy_guidance}\n{base_prompt}"
        
        return enhanced_prompt
    
    def _get_architectural_guidance(self, pattern: ArchitecturalPattern) -> str:
        """Get specific guidance for architectural patterns."""
        guidance = {
            ArchitecturalPattern.FUNCTIONAL: "Use pure functions, immutable data structures, function composition, avoid side effects",
            ArchitecturalPattern.OBJECT_ORIENTED: "Use classes with clear responsibilities, encapsulation, inheritance where appropriate",
            ArchitecturalPattern.PROCEDURAL: "Use simple functions, sequential execution, minimal complex state management",
            ArchitecturalPattern.REACTIVE: "Use event-driven patterns, reactive streams, asynchronous processing",
            ArchitecturalPattern.LAYERED: "Separate concerns into distinct layers (data, business, presentation)",
            ArchitecturalPattern.MICROSERVICE: "Create loosely coupled, independently deployable components"
        }
        return guidance.get(pattern, "Follow standard architectural principles")
    
    def _get_complexity_guidance(self, level: ComplexityLevel) -> str:
        """Get specific guidance for complexity levels."""
        guidance = {
            ComplexityLevel.MINIMAL: "Basic implementation, minimal error handling, simple validation",
            ComplexityLevel.STANDARD: "Good practices, reasonable error handling, input validation, basic logging",
            ComplexityLevel.ROBUST: "Comprehensive error handling, thorough validation, detailed logging, resilience patterns",
            ComplexityLevel.ENTERPRISE: "Full enterprise patterns, monitoring, circuit breakers, health checks, audit trails"
        }
        return guidance.get(level, "Apply standard development practices")
    
    def _get_technology_guidance(self, approach: TechnologyApproach) -> str:
        """Get specific guidance for technology approaches."""
        guidance = {
            TechnologyApproach.MODERN: "Use latest language features, modern libraries, cutting-edge patterns",
            TechnologyApproach.STABLE: "Use proven, well-established libraries and patterns with long-term support",
            TechnologyApproach.PERFORMANCE: "Optimize for speed and efficiency, use performance-oriented libraries",
            TechnologyApproach.SIMPLICITY: "Prioritize code clarity and ease of understanding, avoid complexity"
        }
        return guidance.get(approach, "Balance modern features with stability")


# Integration wrapper for existing prompt builders
class StrategyEnhancedPromptBuilder:
    """Wrapper that adds adaptive strategy selection to existing prompt builders."""
    
    def __init__(self, base_prompt_builder):
        self.base_prompt_builder = base_prompt_builder
        try:
            self.strategist = AdaptiveGenerationStrategist()
            self.strategy_enhancement_enabled = True
        except Exception:
            self.strategy_enhancement_enabled = False
    
    def build_single_blueprint_prompt(self, blueprint, language, context_parts, 
                                    dependency_versions=None) -> str:
        """Build prompt with adaptive strategy enhancement."""
        # Get base prompt
        base_prompt = self.base_prompt_builder.build_single_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )
        
        # Add strategy enhancement if enabled
        if self.strategy_enhancement_enabled:
            try:
                project_context = self.strategist.analyze_project_context(blueprint)
                strategy = self.strategist.select_optimal_strategy(blueprint, project_context, language)
                enhanced_prompt = self.strategist.enhance_prompt_with_strategy(
                    base_prompt, strategy, language
                )
                return enhanced_prompt
            except Exception:
                # Fallback to base prompt on any error
                pass
        
        return base_prompt
    
    def build_natural_blueprint_prompt(self, blueprint, language, context_parts, 
                                     dependency_versions=None) -> str:
        """Build natural language prompt with strategy enhancement."""
        # Get base prompt
        base_prompt = self.base_prompt_builder.build_natural_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )
        
        # Add strategy enhancement if enabled
        if self.strategy_enhancement_enabled:
            try:
                project_context = self.strategist.analyze_project_context(blueprint)
                strategy = self.strategist.select_optimal_strategy(blueprint, project_context, language)
                enhanced_prompt = self.strategist.enhance_prompt_with_strategy(
                    base_prompt, strategy, language
                )
                return enhanced_prompt
            except Exception:
                # Fallback to base prompt on any error
                pass
        
        return base_prompt
    
    # Delegate other methods to base builder
    def __getattr__(self, name):
        return getattr(self.base_prompt_builder, name)