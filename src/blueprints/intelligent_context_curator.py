"""Intelligent context curation using Claude for relevance analysis and optimization."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from anthropic import Anthropic

from .parser import Blueprint
from .constants import DEFAULT_MODEL
from .utils import check_anthropic_api_key


@dataclass
class ContextItem:
    """A piece of context with metadata for curation."""
    content: str
    source_type: str  # "blueprint", "generated_code", "documentation"
    module_name: str
    relevance_score: float = 0.0
    token_estimate: int = 0
    priority: str = "medium"  # "critical", "high", "medium", "low"
    relationships: List[str] = field(default_factory=list)


@dataclass
class CurationResult:
    """Result of context curation with analytics."""
    curated_context: List[str]
    selected_items: List[ContextItem]
    excluded_items: List[ContextItem]
    total_tokens_estimated: int
    curation_reasoning: str
    optimization_applied: List[str]


class ContextRelevanceAnalyzer:
    """Analyzes relevance of context items to the generation goal."""
    
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
    
    def analyze_relevance(self, blueprint: Blueprint, 
                         available_items: List[ContextItem],
                         generation_goal: str) -> List[ContextItem]:
        """Analyze relevance of each context item to the blueprint generation."""
        
        # Create summary of available context for analysis
        context_summary = []
        for item in available_items:
            summary = f"- {item.module_name} ({item.source_type}): {item.content[:200]}..."
            context_summary.append(summary)
        
        analysis_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

TARGET BLUEPRINT TO GENERATE:
Module: {blueprint.module_name}
Description: {blueprint.description}
Content: {blueprint.raw_content[:1000]}

GENERATION GOAL: {generation_goal}

AVAILABLE CONTEXT ITEMS:
{chr(10).join(context_summary[:20])}  # Limit for token efficiency

Analyze the relevance of each context item to generating code for the target blueprint.

Consider:
1. Direct dependencies (imports, uses, extends)
2. Indirect relationships (similar patterns, shared concepts)
3. Architectural context (project structure, conventions)
4. Domain knowledge (business rules, data models)
5. Technical dependencies (databases, APIs, frameworks)

For each context item, determine:
- Relevance score (0.0-1.0, where 1.0 is critical for generation)
- Priority level (critical, high, medium, low)
- Relationships to other items
- Reasoning for the relevance score

Return JSON:
{{
    "analysis": [
        {{
            "module_name": "module name",
            "relevance_score": 0.0-1.0,
            "priority": "critical|high|medium|low", 
            "relationships": ["related", "module", "names"],
            "reasoning": "why this item is relevant or not"
        }}
    ],
    "generation_strategy": "optimal approach based on available context",
    "missing_context": ["what context might be missing but useful"]
}}

Return ONLY the JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            response_text = response.content[0].text
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Update context items with analysis results
                analysis_by_module = {item["module_name"]: item for item in data.get("analysis", [])}
                
                updated_items = []
                for item in available_items:
                    if item.module_name in analysis_by_module:
                        analysis = analysis_by_module[item.module_name]
                        item.relevance_score = analysis.get("relevance_score", 0.5)
                        item.priority = analysis.get("priority", "medium")
                        item.relationships = analysis.get("relationships", [])
                    updated_items.append(item)
                
                return updated_items
                
        except Exception:
            pass
        
        # Fallback: return items with default scores
        return available_items


class ContextOptimizer:
    """Optimizes context size and ordering for maximum effectiveness."""
    
    def __init__(self, client):
        self.client = client
    
    def optimize_context_selection(self, analyzed_items: List[ContextItem],
                                  max_tokens: int = 8000,
                                  blueprint: Optional[Blueprint] = None) -> CurationResult:
        """Select optimal context items within token limits."""
        
        # Sort by relevance and priority
        priority_weights = {"critical": 1000, "high": 100, "medium": 10, "low": 1}
        
        sorted_items = sorted(
            analyzed_items,
            key=lambda x: (priority_weights.get(x.priority, 1) * x.relevance_score),
            reverse=True
        )
        
        # Select items within token budget
        selected_items = []
        excluded_items = []
        current_tokens = 0
        
        for item in sorted_items:
            item_tokens = self._estimate_tokens(item.content)
            item.token_estimate = item_tokens
            
            if current_tokens + item_tokens <= max_tokens:
                selected_items.append(item)
                current_tokens += item_tokens
            else:
                excluded_items.append(item)
        
        # Generate optimized context ordering
        ordered_context = self._create_optimal_ordering(selected_items, blueprint)
        
        curation_reasoning = f"""
Context curation applied:
- Total available items: {len(analyzed_items)}
- Selected items: {len(selected_items)} 
- Excluded items: {len(excluded_items)}
- Token budget: {max_tokens}, Used: {current_tokens}
- Optimization: Sorted by relevance × priority weight
"""
        
        return CurationResult(
            curated_context=ordered_context,
            selected_items=selected_items,
            excluded_items=excluded_items,
            total_tokens_estimated=current_tokens,
            curation_reasoning=curation_reasoning,
            optimization_applied=["relevance_sorting", "token_budgeting", "priority_weighting"]
        )
    
    def _estimate_tokens(self, content: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return len(content) // 4
    
    def _create_optimal_ordering(self, selected_items: List[ContextItem], 
                                blueprint: Optional[Blueprint]) -> List[str]:
        """Create optimally ordered context from selected items."""
        context_parts = []
        
        # Group by priority and type
        critical_items = [item for item in selected_items if item.priority == "critical"]
        high_items = [item for item in selected_items if item.priority == "high"] 
        medium_items = [item for item in selected_items if item.priority == "medium"]
        low_items = [item for item in selected_items if item.priority == "low"]
        
        if selected_items:
            context_parts.extend([
                "=== CURATED CONTEXT ===",
                "The following context has been intelligently selected for relevance:",
                ""
            ])
            
            # Add critical context first
            if critical_items:
                context_parts.append("--- CRITICAL DEPENDENCIES ---")
                for item in critical_items:
                    context_parts.extend([
                        f"Module: {item.module_name} (Priority: {item.priority}, Relevance: {item.relevance_score:.1f})",
                        item.content,
                        ""
                    ])
            
            # Add high priority context
            if high_items:
                context_parts.append("--- HIGH PRIORITY CONTEXT ---")
                for item in high_items:
                    context_parts.extend([
                        f"Module: {item.module_name} (Priority: {item.priority}, Relevance: {item.relevance_score:.1f})", 
                        item.content,
                        ""
                    ])
            
            # Add medium priority context (condensed)
            if medium_items:
                context_parts.append("--- SUPPORTING CONTEXT ---")
                for item in medium_items:
                    # Condense medium priority items
                    condensed = item.content[:500] + ("..." if len(item.content) > 500 else "")
                    context_parts.extend([
                        f"Module: {item.module_name} (Priority: {item.priority}, Relevance: {item.relevance_score:.1f})",
                        condensed,
                        ""
                    ])
            
            context_parts.extend([
                "=== END CURATED CONTEXT ===",
                ""
            ])
        
        return context_parts


class IntelligentContextCurator:
    """Main context curation coordinator using Claude for optimal context selection."""
    
    def __init__(self, max_tokens: int = 8000):
        check_anthropic_api_key("intelligent context curation")
        
        
        self.client = Anthropic()
        
        self.max_tokens = max_tokens
        self.relevance_analyzer = ContextRelevanceAnalyzer(self.client)
        self.context_optimizer = ContextOptimizer(self.client)
    
    def curate_optimal_context(self, blueprint: Blueprint,
                              dependencies: List[Blueprint],
                              generated_context: Dict[str, str],
                              generation_goal: str = "Generate production-ready code") -> CurationResult:
        """Curate optimal context using Claude intelligence."""
        
        # Convert available information to context items
        available_items = []
        
        # Add dependency blueprints
        for dep in dependencies:
            item = ContextItem(
                content=dep.raw_content,
                source_type="blueprint", 
                module_name=dep.module_name,
                priority="medium"
            )
            available_items.append(item)
        
        # Add generated code context
        for module_name, code in generated_context.items():
            item = ContextItem(
                content=f"Generated code:\n{code}",
                source_type="generated_code",
                module_name=module_name,
                priority="high"  # Generated code is usually highly relevant
            )
            available_items.append(item)
        
        # Analyze relevance using Claude
        analyzed_items = self.relevance_analyzer.analyze_relevance(
            blueprint, available_items, generation_goal
        )
        
        # Optimize selection and ordering
        curation_result = self.context_optimizer.optimize_context_selection(
            analyzed_items, self.max_tokens, blueprint
        )
        
        return curation_result
    
    def curate_comprehensive_context(self, resolved_blueprint,
                                   language: str = "python") -> List[str]:
        """Curate context for comprehensive generation (replacement for simple concatenation)."""
        
        # Convert resolved blueprint to context items
        available_items = []
        
        for dep in resolved_blueprint.dependencies:
            item = ContextItem(
                content=dep.raw_content,
                source_type="blueprint",
                module_name=dep.module_name
            )
            available_items.append(item)
        
        # Analyze and optimize context
        generation_goal = f"Generate {language} code following project patterns and dependencies"
        
        analyzed_items = self.relevance_analyzer.analyze_relevance(
            resolved_blueprint.main, available_items, generation_goal
        )
        
        curation_result = self.context_optimizer.optimize_context_selection(
            analyzed_items, self.max_tokens, resolved_blueprint.main
        )
        
        # Add generation goal and instructions
        final_context = curation_result.curated_context.copy()
        final_context.extend([
            f"Now generate {language} code for the following blueprint:",
            f"Module: {resolved_blueprint.main.module_name}",
            resolved_blueprint.main.raw_content,
            "",
            "Use the curated context above to inform your implementation.",
            ""
        ])
        
        return final_context


# Backwards compatibility wrapper
class SmartContextBuilder:
    """Wrapper to maintain compatibility with existing context building interface."""
    
    def __init__(self, max_tokens: int = 8000):
        self.curator = IntelligentContextCurator(max_tokens)
    
    def create_blueprint_context(self, blueprint: Blueprint, resolved_blueprint,
                                generated_context: Dict[str, str], language: str) -> List[str]:
        """Smart context creation using curation (replaces simple concatenation)."""
        try:
            # Get dependencies for this specific blueprint
            dependencies = []
            for ref in blueprint.blueprint_refs:
                for dep in resolved_blueprint.dependencies:
                    if dep.module_name == ref.module_path or ref.module_path in str(dep.file_path or ""):
                        dependencies.append(dep)
            
            curation_result = self.curator.curate_optimal_context(
                blueprint, dependencies, generated_context,
                f"Generate {language} code with proper imports and dependencies"
            )
            
            context_parts = curation_result.curated_context.copy()
            context_parts.extend([
                f"Generate {language} code for:",
                f"Module: {blueprint.module_name}",
                blueprint.raw_content,
                ""
            ])
            
            return context_parts
            
        except Exception:
            # Fallback to simple context on any error
            return self._fallback_context(blueprint, resolved_blueprint, generated_context, language)
    
    def create_comprehensive_context(self, resolved_blueprint, language: str) -> List[str]:
        """Smart comprehensive context creation."""
        try:
            return self.curator.curate_comprehensive_context(resolved_blueprint, language)
        except Exception:
            # Fallback to simple concatenation
            return self._fallback_comprehensive_context(resolved_blueprint, language)
    
    def _fallback_context(self, blueprint, resolved_blueprint, generated_context, language):
        """Fallback to simple context creation."""
        context_parts = ["Generate {} code from this blueprint:".format(language), ""]
        
        # Add some generated context if available
        for module_name, code in list(generated_context.items())[:3]:  # Limit to prevent bloat
            context_parts.extend([
                f"Available module: {module_name}",
                code[:300] + "..." if len(code) > 300 else code,
                ""
            ])
        
        return context_parts
    
    def _fallback_comprehensive_context(self, resolved_blueprint, language):
        """Fallback comprehensive context."""
        context_parts = []
        
        if resolved_blueprint.dependencies:
            context_parts.extend([
                f"Generate {language} code using these dependencies:",
                ""
            ])
            
            # Add first few dependencies to prevent context explosion
            for dep in resolved_blueprint.dependencies[:5]:
                context_parts.extend([
                    f"--- {dep.module_name} ---",
                    dep.raw_content[:400] + "..." if len(dep.raw_content) > 400 else dep.raw_content,
                    ""
                ])
        
        return context_parts