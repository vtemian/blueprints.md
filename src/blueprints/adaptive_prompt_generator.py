"""Self-improving prompt generation using Claude for meta-reasoning about optimal prompts."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from anthropic import Anthropic

from .parser import Blueprint
from .constants import DEFAULT_MODEL
from .logging_config import get_logger
from .utils import check_anthropic_api_key


@dataclass
class PromptResult:
    """Result of using a generated prompt."""
    prompt_id: str
    blueprint_type: str
    language: str
    success: bool
    verification_errors: List[str] = field(default_factory=list)
    generation_time: Optional[float] = None
    code_quality_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PromptTemplate:
    """A Claude-generated prompt template with metadata."""
    template_id: str
    blueprint_type: str
    language: str
    complexity_level: str  # "simple", "medium", "complex"
    prompt_content: str
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


class PromptHistory:
    """Tracks prompt performance and learning data."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.cwd() / ".claude_prompt_history.json"
        self.results: List[PromptResult] = []
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_history()
    
    def add_result(self, result: PromptResult):
        """Add a prompt usage result for learning."""
        self.results.append(result)
        self._update_template_stats(result)
        self._save_history()
    
    def get_best_template(self, blueprint_type: str, language: str, 
                         complexity_level: str) -> Optional[PromptTemplate]:
        """Get the best performing template for given criteria."""
        candidates = [
            t for t in self.templates.values()
            if (t.blueprint_type == blueprint_type and 
                t.language == language and 
                t.complexity_level == complexity_level and
                t.usage_count >= 2)  # Need some data
        ]
        
        if not candidates:
            return None
            
        return max(candidates, key=lambda t: t.success_rate)
    
    def _update_template_stats(self, result: PromptResult):
        """Update template statistics based on result."""
        if result.prompt_id in self.templates:
            template = self.templates[result.prompt_id]
            template.usage_count += 1
            
            # Update success rate
            successful_uses = sum(1 for r in self.results 
                                if r.prompt_id == result.prompt_id and r.success)
            template.success_rate = successful_uses / template.usage_count
            template.last_updated = datetime.now()
    
    def _load_history(self):
        """Load history from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    
                # Load templates
                for t_data in data.get("templates", []):
                    template = PromptTemplate(**t_data)
                    self.templates[template.template_id] = template
                    
            except Exception:
                pass  # Start fresh on any error
    
    def _save_history(self):
        """Save history to storage."""
        try:
            data = {
                "templates": [
                    {
                        "template_id": t.template_id,
                        "blueprint_type": t.blueprint_type,
                        "language": t.language,
                        "complexity_level": t.complexity_level,
                        "prompt_content": t.prompt_content,
                        "success_rate": t.success_rate,
                        "usage_count": t.usage_count,
                        "created_at": t.created_at.isoformat(),
                        "last_updated": t.last_updated.isoformat()
                    }
                    for t in self.templates.values()
                ]
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception:
            pass  # Don't fail on storage errors


class PromptOptimizer:
    """Analyzes prompt performance and generates improvements."""
    
    def __init__(self, client):
        self.client = client
        self._load_blueprint_spec()
    
    def _load_blueprint_spec(self):
        """Load blueprint specification for context."""
        spec_path = Path(__file__).parent.parent.parent / "BLUEPRINTS_SPEC.md"
        if spec_path.exists():
            self.blueprint_spec = spec_path.read_text()
        else:
            self.blueprint_spec = "Natural language blueprint format"
    
    def analyze_failures_and_improve(self, failures: List[PromptResult], 
                                   current_template: PromptTemplate) -> str:
        """Analyze failures and generate improved prompt."""
        failure_analysis = []
        for failure in failures[-5:]:  # Last 5 failures
            failure_analysis.append({
                "errors": failure.verification_errors,
                "blueprint_type": failure.blueprint_type,
                "language": failure.language
            })
        
        improvement_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

CURRENT PROMPT TEMPLATE (Success Rate: {current_template.success_rate:.1%}):
{current_template.prompt_content}

RECENT FAILURES ANALYSIS:
{json.dumps(failure_analysis, indent=2)}

Generate an IMPROVED prompt template that addresses the common failure patterns.

Focus on:
1. Fixing recurring verification errors
2. Better context understanding
3. More precise generation instructions
4. Language-specific optimizations
5. Framework-specific best practices

The improved prompt should:
- Generate more accurate code that passes verification
- Be more specific about common pitfalls
- Include better error handling guidance
- Adapt to the specific blueprint complexity level: {current_template.complexity_level}

Return ONLY the improved prompt template without explanations.
"""
        
        response = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": improvement_prompt}]
        )
        
        return response.content[0].text.strip()


class AdaptivePromptGenerator:
    """Claude-powered prompt generator that learns and improves over time."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        check_anthropic_api_key("adaptive prompt generation")
        
        
        self.client = Anthropic()
        
        self.history = PromptHistory(storage_path)
        self.optimizer = PromptOptimizer(self.client)
        self._load_blueprint_spec()
    
    def _load_blueprint_spec(self):
        """Load blueprint specification for context."""
        spec_path = Path(__file__).parent.parent.parent / "BLUEPRINTS_SPEC.md"
        if spec_path.exists():
            self.blueprint_spec = spec_path.read_text()
        else:
            self.blueprint_spec = "Natural language blueprint format"
    
    def build_single_blueprint_prompt(self, blueprint: Blueprint, language: str,
                                    context_parts: List[str], 
                                    dependency_versions: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
        """Generate adaptive prompt for single blueprint - returns (prompt, prompt_id)."""
        complexity = self._assess_complexity(blueprint)
        
        # Try to get existing high-performing template
        existing_template = self.history.get_best_template("single", language, complexity)
        
        if existing_template and existing_template.success_rate > 0.7:
            # Use existing high-performing template
            prompt_content = self._customize_template(
                existing_template.prompt_content, blueprint, context_parts, dependency_versions
            )
            return prompt_content, existing_template.template_id
        
        # Generate new prompt
        prompt_content, template_id = self._generate_new_prompt(
            "single", blueprint, language, context_parts, complexity, dependency_versions
        )
        
        return prompt_content, template_id
    
    def build_natural_blueprint_prompt(self, blueprint: Blueprint, language: str,
                                     context_parts: List[str],
                                     dependency_versions: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
        """Generate adaptive prompt for natural blueprint - returns (prompt, prompt_id)."""
        complexity = self._assess_complexity(blueprint)
        
        # Try existing template
        existing_template = self.history.get_best_template("natural", language, complexity)
        
        if existing_template and existing_template.success_rate > 0.7:
            prompt_content = self._customize_template(
                existing_template.prompt_content, blueprint, context_parts, dependency_versions
            )
            return prompt_content, existing_template.template_id
        
        # Generate new prompt
        prompt_content, template_id = self._generate_new_prompt(
            "natural", blueprint, language, context_parts, complexity, dependency_versions
        )
        
        return prompt_content, template_id
    
    def record_result(self, prompt_id: str, blueprint: Blueprint, language: str,
                     success: bool, verification_errors: List[str] = None,
                     generation_time: Optional[float] = None):
        """Record the result of using a generated prompt."""
        result = PromptResult(
            prompt_id=prompt_id,
            blueprint_type="natural" if hasattr(blueprint, 'requirements') else "single",
            language=language,
            success=success,
            verification_errors=verification_errors or [],
            generation_time=generation_time
        )
        
        self.history.add_result(result)
        
        # If this prompt is failing, try to improve it
        if not success and prompt_id in self.history.templates:
            self._consider_prompt_improvement(prompt_id)
    
    def _assess_complexity(self, blueprint: Blueprint) -> str:
        """Assess blueprint complexity using Claude."""
        complexity_prompt = f"""
BLUEPRINT TO ANALYZE:
Module: {blueprint.module_name}
Description: {blueprint.description}

{blueprint.raw_content[:1000]}  # First 1000 chars

Analyze this blueprint and classify its complexity level:
- "simple": Basic CRUD, single responsibility, few dependencies
- "medium": Multiple components, some business logic, moderate dependencies  
- "complex": Advanced patterns, heavy integration, many dependencies

Return ONLY: simple, medium, or complex
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=50,
                messages=[{"role": "user", "content": complexity_prompt}]
            )
            
            complexity = response.content[0].text.strip().lower()
            if complexity in ["simple", "medium", "complex"]:
                return complexity
        except Exception:
            pass
        
        # Fallback heuristic
        if len(blueprint.raw_content) < 300:
            return "simple"
        elif len(blueprint.raw_content) < 800:
            return "medium"
        else:
            return "complex"
    
    def _generate_new_prompt(self, blueprint_type: str, blueprint: Blueprint, 
                           language: str, context_parts: List[str], 
                           complexity: str, dependency_versions: Optional[Dict[str, str]]) -> Tuple[str, str]:
        """Generate a new optimized prompt using Claude meta-reasoning."""
        
        context_summary = "\n".join(context_parts[:3])  # Limit for token efficiency
        
        meta_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

TASK: Generate an optimal prompt for Claude to generate {language} code from this blueprint.

BLUEPRINT TO ANALYZE:
Type: {blueprint_type}
Complexity: {complexity}
Module: {blueprint.module_name}
Description: {blueprint.description}
Content: {blueprint.raw_content[:1500]}

CONTEXT AVAILABLE:
{context_summary[:1000] if context_summary else "None"}

DEPENDENCY VERSIONS:
{json.dumps(dependency_versions) if dependency_versions else "None"}

REQUIREMENTS FOR THE GENERATED PROMPT:
1. Must be highly specific to this {complexity} {blueprint_type} blueprint
2. Should include context-aware coding guidelines for {language}
3. Must address common pitfalls for this type of blueprint
4. Should generate production-ready, well-structured code
5. Include specific error handling and validation appropriate for this complexity
6. Add framework-specific best practices if applicable
7. Must be clear about imports, dependencies, and module structure

OPTIMIZATION GOALS:
- Generate code that passes verification on first try
- Minimize common errors for {language} and this blueprint type
- Include enough context without overwhelming Claude
- Be specific about the expected output format and structure

Generate the optimal prompt that Claude should receive to generate the best possible {language} code for this blueprint.

Return ONLY the prompt without explanations or meta-commentary.
"""
        
        response = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": meta_prompt}]
        )
        
        generated_prompt = response.content[0].text.strip()
        
        # Store as new template
        template_id = f"{blueprint_type}_{language}_{complexity}_{len(self.history.templates)}"
        template = PromptTemplate(
            template_id=template_id,
            blueprint_type=blueprint_type,
            language=language,
            complexity_level=complexity,
            prompt_content=generated_prompt
        )
        
        self.history.templates[template_id] = template
        
        return generated_prompt, template_id
    
    def _customize_template(self, template: str, blueprint: Blueprint,
                          context_parts: List[str], 
                          dependency_versions: Optional[Dict[str, str]]) -> str:
        """Customize existing template with specific blueprint details."""
        # Simple template customization - could be enhanced
        customized = template.replace("{{MODULE_NAME}}", blueprint.module_name)
        customized = customized.replace("{{DESCRIPTION}}", blueprint.description)
        
        if context_parts:
            context_section = "\n".join(context_parts[:3])
            customized = f"{context_section}\n\n{customized}"
        
        return customized
    
    def _consider_prompt_improvement(self, prompt_id: str):
        """Consider improving a prompt if it's failing too much."""
        template = self.history.templates.get(prompt_id)
        if not template or template.usage_count < 3:
            return  # Need more data
        
        if template.success_rate < 0.5:  # Less than 50% success
            # Get recent failures
            failures = [r for r in self.history.results 
                       if r.prompt_id == prompt_id and not r.success][-5:]
            
            if len(failures) >= 3:  # Enough failure data
                try:
                    improved_prompt = self.optimizer.analyze_failures_and_improve(failures, template)
                    
                    # Create new improved template
                    new_template_id = f"{template.template_id}_improved_{int(datetime.now().timestamp())}"
                    new_template = PromptTemplate(
                        template_id=new_template_id,
                        blueprint_type=template.blueprint_type,
                        language=template.language,
                        complexity_level=template.complexity_level,
                        prompt_content=improved_prompt
                    )
                    
                    self.history.templates[new_template_id] = new_template
                    
                except Exception:
                    pass  # Don't fail on improvement errors


# Compatibility wrapper to maintain existing interface
class AdaptivePromptBuilder:
    """Wrapper to maintain compatibility with existing PromptBuilder interface."""
    
    def __init__(self):
        self.adaptive_generator = AdaptivePromptGenerator()
        self._prompt_ids = {}  # Track prompt IDs for results
        
        # Add strategy enhancement layer (lazy loading to avoid circular imports)
        self.strategy_enhanced = None
        self.strategy_enabled = False
        
        # Recursion prevention
        self._recursion_depth = 0
        self._max_recursion_depth = 3
    
    def build_single_blueprint_prompt(self, blueprint: Blueprint, language: str,
                                    context_parts: List[str],
                                    dependency_versions: Optional[Dict[str, str]] = None) -> str:
        """Build prompt using adaptive generation with strategy enhancement."""
        logger = get_logger('prompt_builder')
        logger.debug(f"Building prompt for {blueprint.module_name} ({language})")
        logger.debug(f"Context parts: {len(context_parts)}, Dependencies: {len(dependency_versions) if dependency_versions else 0}")
        
        # Use strategy enhancement with recursion protection
        self._recursion_depth += 1
        
        if self._recursion_depth > self._max_recursion_depth:
            logger.warning(f"Max recursion depth ({self._max_recursion_depth}) reached, using base generation")
            self._recursion_depth -= 1
        else:
            if not self.strategy_enabled:
                logger.debug("Initializing strategy enhancement...")
                self._init_strategy_enhancement()
            
            if self.strategy_enabled and self.strategy_enhanced:
                logger.debug(f"Using strategy-enhanced prompt generation (depth: {self._recursion_depth})...")
                try:
                    result = self.strategy_enhanced.build_single_blueprint_prompt(
                        blueprint, language, context_parts, dependency_versions
                    )
                    logger.debug(f"Strategy-enhanced prompt generated ({len(result)} chars)")
                    self._recursion_depth -= 1
                    return result
                except Exception as e:
                    logger.warning(f"Strategy enhancement failed: {e}, falling back to base generation")
            
            self._recursion_depth -= 1
        
        # Base adaptive generation
        logger.debug("Using base adaptive generation...")
        prompt, prompt_id = self.adaptive_generator.build_single_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )
        
        # Store prompt ID for later result recording
        self._prompt_ids[id(blueprint)] = prompt_id
        logger.debug(f"Base adaptive prompt generated ({len(prompt)} chars), ID: {prompt_id}")
        
        return prompt
    
    def build_natural_blueprint_prompt(self, blueprint: Blueprint, language: str,
                                     context_parts: List[str],
                                     dependency_versions: Optional[Dict[str, str]] = None) -> str:
        """Build prompt using adaptive generation with strategy enhancement."""
        logger = get_logger('prompt_builder')
        logger.debug(f"Building natural prompt for {blueprint.module_name} ({language})")
        logger.debug(f"Context parts: {len(context_parts)}, Dependencies: {len(dependency_versions) if dependency_versions else 0}")
        
        # Use strategy enhancement with recursion protection
        self._recursion_depth += 1
        
        if self._recursion_depth > self._max_recursion_depth:
            logger.warning(f"Max recursion depth ({self._max_recursion_depth}) reached, using base generation")
            self._recursion_depth -= 1
        else:
            if not self.strategy_enabled:
                logger.debug("Initializing strategy enhancement...")
                self._init_strategy_enhancement()
                
            if self.strategy_enabled and self.strategy_enhanced:
                logger.debug(f"Using strategy-enhanced natural prompt generation (depth: {self._recursion_depth})...")
                try:
                    result = self.strategy_enhanced.build_natural_blueprint_prompt(
                        blueprint, language, context_parts, dependency_versions
                    )
                    logger.debug(f"Strategy-enhanced natural prompt generated ({len(result)} chars)")
                    self._recursion_depth -= 1
                    return result
                except Exception as e:
                    logger.warning(f"Strategy enhancement failed: {e}, falling back to base generation")
            
            self._recursion_depth -= 1
        
        # Base adaptive generation
        logger.debug("Using base adaptive natural generation...")
        prompt, prompt_id = self.adaptive_generator.build_natural_blueprint_prompt(
            blueprint, language, context_parts, dependency_versions
        )
        
        # Store prompt ID for later result recording
        self._prompt_ids[id(blueprint)] = prompt_id
        logger.debug(f"Base adaptive natural prompt generated ({len(prompt)} chars), ID: {prompt_id}")
        
        return prompt
    
    def _init_strategy_enhancement(self):
        """Lazy initialization of strategy enhancement to avoid circular imports."""
        try:
            from .adaptive_generation_strategist import StrategyEnhancedPromptBuilder
            self.strategy_enhanced = StrategyEnhancedPromptBuilder(self)
            self.strategy_enabled = True
        except Exception:
            self.strategy_enabled = False
    
    def record_generation_result(self, blueprint: Blueprint, language: str,
                               success: bool, verification_errors: List[str] = None):
        """Record result for learning (new method for feedback)."""
        blueprint_id = id(blueprint)
        if blueprint_id in self._prompt_ids:
            self.adaptive_generator.record_result(
                self._prompt_ids[blueprint_id], blueprint, language,
                success, verification_errors
            )