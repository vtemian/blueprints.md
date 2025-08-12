"""Iterative quality improvement system using Claude for self-review and refinement of generated code."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from anthropic import Anthropic

from .parser import Blueprint
from .constants import DEFAULT_MODEL
from .utils import check_anthropic_api_key


class QualityDimension(Enum):
    """Quality dimensions for code assessment."""
    CORRECTNESS = "correctness"
    READABILITY = "readability"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    BEST_PRACTICES = "best_practices"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"


@dataclass
class QualityScore:
    """Score for a specific quality dimension."""
    dimension: QualityDimension
    score: float  # 0.0 to 1.0
    reasoning: str
    specific_issues: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """Comprehensive quality assessment of generated code."""
    overall_score: float
    dimension_scores: List[QualityScore]
    critical_issues: List[str]
    improvement_priorities: List[str]
    strengths: List[str]
    assessment_reasoning: str
    blueprint_alignment: float  # How well code matches blueprint requirements


@dataclass
class ImprovementIteration:
    """Single iteration of code improvement."""
    iteration_number: int
    original_code: str
    improved_code: str
    quality_before: QualityAssessment
    quality_after: QualityAssessment
    improvements_made: List[str]
    time_taken: float
    improvement_reasoning: str


class CodeReviewAgent:
    """Claude-powered agent for reviewing generated code quality."""
    
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
    
    def review_code_quality(self, code: str, blueprint: Blueprint, 
                           language: str = "python") -> QualityAssessment:
        """Perform comprehensive quality review of generated code."""
        
        review_prompt = f"""
BLUEPRINT SPECIFICATION:
{self.blueprint_spec}

TARGET BLUEPRINT:
Module: {blueprint.module_name}
Description: {blueprint.description}
Requirements: {getattr(blueprint, 'requirements', [])}
Content: {blueprint.raw_content[:1000]}

GENERATED CODE TO REVIEW:
```{language}
{code}
```

Perform a comprehensive quality review of this {language} code against the blueprint requirements.

Assess these quality dimensions (score 0.0-1.0):
1. CORRECTNESS: Does the code correctly implement the blueprint requirements?
2. READABILITY: Is the code clear, well-structured, and easy to understand?
3. PERFORMANCE: Are there obvious performance issues or inefficiencies?
4. SECURITY: Are there security vulnerabilities or best practices violations?
5. MAINTAINABILITY: Is the code easy to modify and extend?
6. BEST_PRACTICES: Does it follow {language} best practices and conventions?
7. ERROR_HANDLING: Are errors handled appropriately?
8. DOCUMENTATION: Are docstrings and comments adequate?

Return JSON:
{{
    "overall_score": 0.0-1.0,
    "dimension_scores": [
        {{
            "dimension": "correctness",
            "score": 0.0-1.0,
            "reasoning": "detailed reasoning for score",
            "specific_issues": ["issue 1", "issue 2"],
            "improvement_suggestions": ["suggestion 1", "suggestion 2"]
        }}
    ],
    "critical_issues": ["critical problems that must be fixed"],
    "improvement_priorities": ["highest priority improvements"],
    "strengths": ["what the code does well"],
    "assessment_reasoning": "overall assessment summary",
    "blueprint_alignment": 0.0-1.0
}}

Be thorough and specific in your assessment. Focus on practical improvements.

Return ONLY the JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=3000,
                messages=[{"role": "user", "content": review_prompt}]
            )
            
            response_text = response.content[0].text
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Convert to QualityAssessment object
                dimension_scores = []
                for dim_data in data.get("dimension_scores", []):
                    dimension = QualityDimension(dim_data["dimension"])
                    score_obj = QualityScore(
                        dimension=dimension,
                        score=dim_data["score"],
                        reasoning=dim_data["reasoning"],
                        specific_issues=dim_data.get("specific_issues", []),
                        improvement_suggestions=dim_data.get("improvement_suggestions", [])
                    )
                    dimension_scores.append(score_obj)
                
                return QualityAssessment(
                    overall_score=data["overall_score"],
                    dimension_scores=dimension_scores,
                    critical_issues=data.get("critical_issues", []),
                    improvement_priorities=data.get("improvement_priorities", []),
                    strengths=data.get("strengths", []),
                    assessment_reasoning=data.get("assessment_reasoning", ""),
                    blueprint_alignment=data.get("blueprint_alignment", 0.7)
                )
                
        except Exception:
            pass
        
        # Fallback assessment
        return self._create_fallback_assessment()
    
    def _create_fallback_assessment(self) -> QualityAssessment:
        """Create basic fallback assessment."""
        return QualityAssessment(
            overall_score=0.7,
            dimension_scores=[],
            critical_issues=[],
            improvement_priorities=["Review code manually"],
            strengths=["Code generated successfully"],
            assessment_reasoning="Unable to perform detailed assessment",
            blueprint_alignment=0.7
        )


class CodeImprover:
    """Claude-powered agent for improving code based on quality assessment."""
    
    def __init__(self, client):
        self.client = client
    
    def improve_code(self, code: str, blueprint: Blueprint, 
                    quality_assessment: QualityAssessment,
                    language: str = "python") -> Tuple[str, List[str]]:
        """Improve code based on quality assessment."""
        
        # Focus on the most critical improvements
        priority_issues = quality_assessment.critical_issues[:3]  # Top 3 critical
        priority_improvements = quality_assessment.improvement_priorities[:3]  # Top 3 priorities
        
        # Get specific suggestions from low-scoring dimensions
        specific_suggestions = []
        for dim_score in quality_assessment.dimension_scores:
            if dim_score.score < 0.7:  # Focus on dimensions that need improvement
                specific_suggestions.extend(dim_score.improvement_suggestions[:2])
        
        improvement_prompt = f"""
ORIGINAL CODE TO IMPROVE:
```{language}
{code}
```

BLUEPRINT REQUIREMENTS:
Module: {blueprint.module_name}
Description: {blueprint.description}
Requirements: {getattr(blueprint, 'requirements', [])}

QUALITY ASSESSMENT RESULTS:
Overall Score: {quality_assessment.overall_score:.1f}
Blueprint Alignment: {quality_assessment.blueprint_alignment:.1f}

CRITICAL ISSUES TO FIX:
{chr(10).join(f"- {issue}" for issue in priority_issues)}

PRIORITY IMPROVEMENTS:
{chr(10).join(f"- {improvement}" for improvement in priority_improvements)}

SPECIFIC SUGGESTIONS:
{chr(10).join(f"- {suggestion}" for suggestion in specific_suggestions[:5])}

IMPROVEMENT GOALS:
1. Fix all critical issues identified
2. Address priority improvements 
3. Improve low-scoring quality dimensions
4. Maintain or improve blueprint alignment
5. Preserve existing functionality that works well

Generate improved {language} code that addresses these issues while maintaining the core functionality.

Focus on:
- Correctness and blueprint requirement fulfillment
- Code readability and clarity
- Proper error handling
- Security best practices
- Performance optimizations where appropriate

Return ONLY the improved code without explanations.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=4000,
                messages=[{"role": "user", "content": improvement_prompt}]
            )
            
            improved_code = response.content[0].text.strip()
            
            # Remove code block markers if present
            if improved_code.startswith(f"```{language}"):
                improved_code = improved_code.split('\n', 1)[1]
            if improved_code.endswith("```"):
                improved_code = improved_code.rsplit('\n', 1)[0]
            
            improvements_made = priority_issues + priority_improvements + specific_suggestions[:3]
            
            return improved_code, improvements_made
            
        except Exception:
            # Return original code if improvement fails
            return code, ["Improvement failed - returned original code"]


class QualityAnalyzer:
    """Analyzes quality trends and improvement effectiveness."""
    
    def __init__(self):
        self.improvement_history: List[ImprovementIteration] = []
    
    def analyze_improvement(self, iteration: ImprovementIteration) -> Dict[str, float]:
        """Analyze the effectiveness of an improvement iteration."""
        quality_delta = iteration.quality_after.overall_score - iteration.quality_before.overall_score
        blueprint_alignment_delta = (iteration.quality_after.blueprint_alignment - 
                                   iteration.quality_before.blueprint_alignment)
        
        # Analyze dimension-specific improvements
        dimension_improvements = {}
        before_dims = {dim.dimension: dim.score for dim in iteration.quality_before.dimension_scores}
        after_dims = {dim.dimension: dim.score for dim in iteration.quality_after.dimension_scores}
        
        for dimension in QualityDimension:
            before_score = before_dims.get(dimension, 0.7)
            after_score = after_dims.get(dimension, 0.7)
            dimension_improvements[dimension.value] = after_score - before_score
        
        return {
            "overall_improvement": quality_delta,
            "blueprint_alignment_improvement": blueprint_alignment_delta,
            "critical_issues_resolved": len(iteration.quality_before.critical_issues) - 
                                       len(iteration.quality_after.critical_issues),
            **dimension_improvements
        }
    
    def should_continue_improving(self, iteration: ImprovementIteration, 
                                 max_iterations: int) -> bool:
        """Determine if further improvement iterations are beneficial."""
        if iteration.iteration_number >= max_iterations:
            return False
        
        # Continue if overall score is still low
        if iteration.quality_after.overall_score < 0.8:
            return True
        
        # Continue if there are still critical issues
        if iteration.quality_after.critical_issues:
            return True
        
        # Continue if blueprint alignment is poor
        if iteration.quality_after.blueprint_alignment < 0.85:
            return True
        
        # Stop if improvement was minimal
        quality_improvement = (iteration.quality_after.overall_score - 
                             iteration.quality_before.overall_score)
        if quality_improvement < 0.05:  # Less than 5% improvement
            return False
        
        return False


class IterativeQualityImprover:
    """Main orchestrator for iterative code quality improvement."""
    
    def __init__(self, max_iterations: int = 3):
        check_anthropic_api_key("iterative quality improvement")
        
        
        self.client = Anthropic()
        
        self.max_iterations = max_iterations
        self.code_reviewer = CodeReviewAgent(self.client)
        self.code_improver = CodeImprover(self.client)
        self.quality_analyzer = QualityAnalyzer()
    
    def improve_code_iteratively(self, initial_code: str, blueprint: Blueprint,
                                language: str = "python") -> Tuple[str, List[ImprovementIteration]]:
        """Perform iterative code improvement until quality targets are met."""
        
        current_code = initial_code
        iterations = []
        
        for iteration_num in range(1, self.max_iterations + 1):
            start_time = datetime.now()
            
            # Assess current code quality
            quality_before = self.code_reviewer.review_code_quality(
                current_code, blueprint, language
            )
            
            # Improve the code
            improved_code, improvements_made = self.code_improver.improve_code(
                current_code, blueprint, quality_before, language
            )
            
            # Assess improved code quality
            quality_after = self.code_reviewer.review_code_quality(
                improved_code, blueprint, language
            )
            
            end_time = datetime.now()
            time_taken = (end_time - start_time).total_seconds()
            
            # Create improvement iteration record
            iteration = ImprovementIteration(
                iteration_number=iteration_num,
                original_code=current_code,
                improved_code=improved_code,
                quality_before=quality_before,
                quality_after=quality_after,
                improvements_made=improvements_made,
                time_taken=time_taken,
                improvement_reasoning=f"Iteration {iteration_num}: {quality_after.assessment_reasoning}"
            )
            
            iterations.append(iteration)
            
            # Analyze improvement effectiveness
            improvement_analysis = self.quality_analyzer.analyze_improvement(iteration)
            
            # Decide whether to continue
            should_continue = self.quality_analyzer.should_continue_improving(
                iteration, self.max_iterations
            )
            
            # Update current code for next iteration
            current_code = improved_code
            
            # Stop if no further improvement is needed
            if not should_continue:
                break
        
        return current_code, iterations
    
    def get_improvement_summary(self, iterations: List[ImprovementIteration]) -> Dict:
        """Generate summary of improvement process."""
        if not iterations:
            return {"error": "No iterations completed"}
        
        first_iteration = iterations[0]
        last_iteration = iterations[-1]
        
        total_improvement = (last_iteration.quality_after.overall_score - 
                           first_iteration.quality_before.overall_score)
        
        blueprint_alignment_improvement = (last_iteration.quality_after.blueprint_alignment -
                                         first_iteration.quality_before.blueprint_alignment)
        
        return {
            "iterations_completed": len(iterations),
            "initial_quality_score": first_iteration.quality_before.overall_score,
            "final_quality_score": last_iteration.quality_after.overall_score,
            "total_improvement": total_improvement,
            "initial_blueprint_alignment": first_iteration.quality_before.blueprint_alignment,
            "final_blueprint_alignment": last_iteration.quality_after.blueprint_alignment,
            "blueprint_alignment_improvement": blueprint_alignment_improvement,
            "critical_issues_resolved": len(first_iteration.quality_before.critical_issues) - 
                                       len(last_iteration.quality_after.critical_issues),
            "total_time_taken": sum(it.time_taken for it in iterations),
            "improvements_made": [imp for it in iterations for imp in it.improvements_made]
        }


# Backwards compatibility wrapper
class QualityEnhancedCodeGenerator:
    """Wrapper that adds iterative quality improvement to existing code generation."""
    
    def __init__(self, base_generator, max_iterations: int = 2):
        """Initialize with a base code generator and quality improvement settings."""
        self.base_generator = base_generator
        try:
            self.quality_improver = IterativeQualityImprover(max_iterations)
            self.quality_improvement_enabled = True
        except Exception:
            self.quality_improvement_enabled = False
    
    def generate_single_blueprint(self, blueprint, context_parts, language="python", 
                                 dependency_versions=None, enable_quality_improvement=True):
        """Generate blueprint with optional quality improvement."""
        # Generate initial code using base generator
        initial_code = self.base_generator.generate_single_blueprint(
            blueprint, context_parts, language, dependency_versions
        )
        
        # Apply quality improvement if enabled and available
        if enable_quality_improvement and self.quality_improvement_enabled:
            try:
                improved_code, iterations = self.quality_improver.improve_code_iteratively(
                    initial_code, blueprint, language
                )
                return improved_code
            except Exception:
                # Fallback to original code if improvement fails
                return initial_code
        
        return initial_code
    
    def generate_natural_blueprint(self, blueprint, context_parts, language="python",
                                  dependency_versions=None, enable_quality_improvement=True):
        """Generate natural blueprint with optional quality improvement."""
        # Generate initial code using base generator
        initial_code = self.base_generator.generate_natural_blueprint(
            blueprint, context_parts, language, dependency_versions
        )
        
        # Apply quality improvement if enabled and available
        if enable_quality_improvement and self.quality_improvement_enabled:
            try:
                improved_code, iterations = self.quality_improver.improve_code_iteratively(
                    initial_code, blueprint, language
                )
                return improved_code
            except Exception:
                # Fallback to original code if improvement fails
                return initial_code
        
        return initial_code
    
    def generate_single_with_context(self, resolved, output_path, language="python", 
                                   force=False, verify=True):
        """Delegate to base generator - quality improvement handled at lower level."""
        return self.base_generator.generate_single_with_context(
            resolved, output_path, language, force, verify
        )
    
    def generate_project(self, resolved, output_dir, language="python", 
                        force=False, main_md_path=None, verify=True):
        """Delegate to base generator - quality improvement handled at lower level."""
        return self.base_generator.generate_project(
            resolved, output_dir, language, force, main_md_path, verify
        )
    
    # Delegate other methods to base generator
    def __getattr__(self, name):
        return getattr(self.base_generator, name)