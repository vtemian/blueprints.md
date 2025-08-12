from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import ast
import json
import re
import os

from anthropic import Anthropic

from .constants import DEFAULT_MODEL
from .logging_config import get_logger
from .utils import check_anthropic_api_key


@dataclass
class VerificationResult:
    """Result of a code verification check"""
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    suggestions: List[str] = field(default_factory=list)


class CodeVerifier:
    """Claude-powered code verifier with dynamic verification prompts"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self._verification_cache = {}
        
        # Require ANTHROPIC_API_KEY
        check_anthropic_api_key("code verification")
        
        
        self.client = Anthropic()

    def verify_syntax(self, code: str) -> VerificationResult:
        """Check if code has valid Python syntax"""
        logger = get_logger('verifier')
        try:
            ast.parse(code)
            logger.debug(f"Syntax validation passed ({len(code)} characters)")
            return VerificationResult(success=True)
        except SyntaxError as e:
            logger.debug(f"Syntax error at line {e.lineno}: {str(e)}")
            return VerificationResult(
                success=False,
                error_type="syntax",
                error_message=f"Syntax error: {str(e)}",
                error_line=e.lineno,
                suggestions=["Fix the syntax error and try again"]
            )

    def verify_imports(self, code: str) -> VerificationResult:
        """Check for missing imports, relative import issues, and incorrect third-party imports"""
        logger = get_logger('verifier')
        
        # Check for relative import issues (these are structural problems)
        relative_import_issues = self._check_relative_imports(code)
        
        # Use Claude to analyze imports for missing and incorrect patterns
        import_analysis = self._get_common_import_mappings(code)
        
        issues = []
        warnings = []
        
        if relative_import_issues:
            issues.extend(relative_import_issues)
        
        # Check for incorrect imports (these are more serious than missing ones)
        incorrect_imports = [k for k in import_analysis.keys() if k.startswith('incorrect_')]
        if incorrect_imports:
            for incorrect_key in incorrect_imports:
                problematic = incorrect_key.replace('incorrect_', '')
                correct = import_analysis[incorrect_key]
                issues.append(f"Incorrect import: '{problematic}' should be '{correct}'")
        
        # Collect missing imports as warnings
        missing_imports = [k for k in import_analysis.keys() if not k.startswith('incorrect_')]
        if missing_imports:
            warnings.extend([f"Missing import: {import_analysis[k]}" for k in missing_imports])
        
        # Fail verification for structural issues and incorrect imports
        if relative_import_issues or incorrect_imports:
            error_message = "Import issues found"
            if incorrect_imports:
                error_message = f"Incorrect third-party imports detected: {len(incorrect_imports)} issues"
            
            logger.debug(f"Import issues found: {len(issues)} critical issues")
            return VerificationResult(
                success=False,
                error_type="import",
                error_message=error_message,
                suggestions=issues
            )
        
        # Log missing imports as warnings but don't fail verification
        if warnings:
            logger.debug(f"Import warnings (expected for generated code): {len(warnings)} missing imports")
            for warning in warnings:
                logger.debug(f"  - {warning}")
        
        return VerificationResult(success=True)

    def verify_blueprint_requirements(self, code: str, blueprint: "Blueprint") -> VerificationResult:
        """Verify code implements key requirements from blueprint using Claude"""
        try:
            # Generate verification prompt based on blueprint
            verification_prompt = self._generate_verification_prompt(blueprint)
            
            # Use Claude to verify the code against requirements
            verification_result = self._verify_with_claude(code, verification_prompt)
            
            if verification_result['success']:
                return VerificationResult(success=True)
            else:
                return VerificationResult(
                    success=False,
                    error_type="blueprint",
                    error_message="Blueprint requirements not fully implemented",
                    suggestions=verification_result['issues']
                )
        except Exception as e:
            return VerificationResult(
                success=False,
                error_type="verification_error",
                error_message=f"Verification failed: {str(e)}",
                suggestions=["Try regenerating the code"]
            )

    def verify_all(self, code: str, blueprint: Optional["Blueprint"] = None) -> List[VerificationResult]:
        """Run all essential verifications"""
        logger = get_logger('verifier')
        logger.info("Starting code verification...")
        results = []

        # Always check syntax first
        logger.debug("Checking syntax...")
        syntax_result = self.verify_syntax(code)
        results.append(syntax_result)
        if not syntax_result.success:
            logger.warning(f"Syntax error found: {syntax_result.error_message}")
            return results
        logger.debug("✓ Syntax check passed")

        # Check imports
        logger.debug("Checking imports...")
        import_result = self.verify_imports(code)
        results.append(import_result)
        if import_result.success:
            logger.debug("✓ Import check passed")
        else:
            logger.warning(f"Import issues found: {len(import_result.suggestions)} suggestions")

        # Check blueprint requirements if provided
        if blueprint:
            logger.debug(f"Checking blueprint requirements for: {blueprint.module_name}")
            blueprint_result = self.verify_blueprint_requirements(code, blueprint)
            results.append(blueprint_result)
            if blueprint_result.success:
                logger.debug("✓ Blueprint requirements check passed")
            else:
                logger.warning(f"Blueprint requirements not met: {blueprint_result.error_message}")

        logger.info(f"Verification completed: {sum(1 for r in results if r.success)}/{len(results)} checks passed")
        return results

    def _generate_verification_prompt(self, blueprint: "Blueprint") -> str:
        """Generate a verification prompt based on blueprint requirements"""
        cache_key = f"{blueprint.module_name}_{hash(blueprint.raw_content)}"
        
        if cache_key in self._verification_cache:
            return self._verification_cache[cache_key]
        
        prompt_generation = f"""
Based on this blueprint specification, generate a concise verification checklist:

BLUEPRINT:
{blueprint.raw_content}

Generate a JSON response with verification criteria:
{{
    "core_requirements": ["requirement 1", "requirement 2", ...],
    "framework_patterns": ["pattern 1", "pattern 2", ...],
    "implementation_details": ["detail 1", "detail 2", ...]
}}

Focus on:
1. Core functionality mentioned in the blueprint
2. Framework and library patterns used
3. Implementation requirements (endpoints, models, database setup, etc.)

Keep it practical and verifiable from code inspection.
        """
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt_generation}]
            )
            
            verification_prompt = response.content[0].text
            self._verification_cache[cache_key] = verification_prompt
            return verification_prompt
            
        except Exception as e:
            # Fallback to basic verification
            fallback_prompt = f"Verify that the code implements the requirements from: {blueprint.description}"
            self._verification_cache[cache_key] = fallback_prompt
            return fallback_prompt

    def _verify_with_claude(self, code: str, verification_prompt: str) -> dict:
        """Use Claude to verify code against requirements"""
        verification_request = f"""
VERIFICATION TASK:
{verification_prompt}

CODE TO VERIFY:
```python
{code}
```

Analyze the code and respond with JSON:
{{
    "success": true/false,
    "issues": ["issue 1", "issue 2", ...],
    "score": 0-100
}}

Focus on:
1. Are the core requirements from the blueprint implemented?
2. Is the code structure and library usage appropriate?
3. Are there obvious missing pieces or incomplete implementations?

Be practical - minor style issues don't matter, focus on functional completeness.
        """
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": verification_request}]
            )
            
            response_text = response.content[0].text
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'success': result.get('success', False),
                    'issues': result.get('issues', []),
                    'score': result.get('score', 0)
                }
            
            # Fallback parsing
            success = 'success": true' in response_text.lower() or 'looks good' in response_text.lower()
            return {
                'success': success,
                'issues': ["Could not parse verification response properly"],
                'score': 50 if success else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'issues': [f"Verification service error: {str(e)}"],
                'score': 0
            }

    def _find_missing_imports(self, code: str) -> List[str]:
        """Find commonly used functions that are missing their imports"""
        function_imports = self._get_common_import_mappings(code)
        
        existing_imports = self._extract_imported_names(code)
        missing = []
        
        for function, import_statement in function_imports.items():
            if function in code and function not in existing_imports:
                if not self._is_function_imported(function, code):
                    missing.append(import_statement)
        
        return missing

    def _get_common_import_mappings(self, code: str) -> dict[str, str]:
        """Get import mappings using Claude-based analysis"""
        try:
            import_analysis = self._analyze_imports_with_claude(code)
            return import_analysis
        except Exception:
            # If Claude analysis fails, return empty dict (no import suggestions)
            return {}
    
    def _analyze_imports_with_claude(self, code: str) -> dict[str, str]:
        """Use Claude to analyze what imports are missing and incorrect"""
        import_request = f"""
Analyze this Python code for import issues, focusing on correctness and third-party library best practices:

```python
{code}
```

ANALYSIS OBJECTIVES:
1. Identify missing imports for functions/classes that are used but not imported
2. Detect imports from incorrect modules (common mistakes in popular libraries)
3. Check for import statement correctness and suggest fixes
4. Validate third-party library usage patterns based on the libraries detected in the code

INSTRUCTIONS:
- Examine all used functions, classes, and modules in the code
- For any third-party libraries you recognize, verify the import paths are correct
- Look for common import mistakes (wrong module paths, incorrect submodules)
- Consider the context of the code to determine appropriate import sources
- Be thorough but only suggest imports that are clearly needed

Return JSON with your analysis:
{{
    "missing_imports": {{
        "item_name": "correct import statement"
    }},
    "incorrect_imports": {{
        "problematic_line": "corrected import statement"
    }},
    "suggestions": [
        "Specific suggestions for import improvements"
    ]
}}

Focus on accuracy - only suggest corrections you're confident about based on standard library usage patterns.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": import_request}]
            )
            
            response_text = response.content[0].text
            logger = get_logger('verifier')
            
            # Extract JSON from response - handle nested braces better
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    import_analysis = json.loads(json_match.group())
                    
                    # Convert analysis to import mappings for backward compatibility
                    # but also log any incorrect imports found
                    mappings = {}
                    
                    # Add missing imports to mappings
                    if 'missing_imports' in import_analysis:
                        mappings.update(import_analysis['missing_imports'])
                    
                    # Log incorrect imports as warnings
                    if 'incorrect_imports' in import_analysis:
                        for problematic, correct in import_analysis['incorrect_imports'].items():
                            logger.warning(f"Incorrect import detected: '{problematic}' should be '{correct}'")
                            mappings[f"incorrect_{problematic}"] = correct
                    
                    # Log suggestions
                    if 'suggestions' in import_analysis:
                        for suggestion in import_analysis['suggestions']:
                            logger.debug(f"Import suggestion: {suggestion}")
                    
                    return mappings
                    
                except json.JSONDecodeError:
                    logger.debug("Failed to parse Claude's import analysis as JSON, falling back to simple parsing")
                    return {}
            
            return {}
            
        except Exception as e:
            logger.debug(f"Claude import analysis failed: {e}")
            return {}

    def _extract_imported_names(self, code: str) -> set:
        """Extract names that are imported in the code"""
        imported = set()
        
        for line in code.splitlines():
            line = line.strip()
            if line.startswith('from ') and ' import ' in line:
                # Handle: from module import name1, name2
                import_part = line.split(' import ')[1]
                names = import_part.replace(' as ', ',').split(',')
                imported.update(name.strip() for name in names)
            elif line.startswith('import '):
                # Handle: import module
                module = line.replace('import ', '').strip()
                imported.add(module)
        
        return imported

    def _check_relative_imports(self, code: str) -> List[str]:
        """Check for problematic relative import patterns"""
        logger = get_logger('verifier')
        issues = []
        
        for line_num, line in enumerate(code.splitlines(), 1):
            line = line.strip()
            if line.startswith('from ..') and 'import' in line:
                # This is a relative import that might cause issues when running as main module
                logger.debug(f"Found relative import on line {line_num}: {line}")
                
                # Extract the import path and suggest absolute import
                parts = line.split()
                if len(parts) >= 4 and parts[0] == 'from' and parts[2] == 'import':
                    relative_path = parts[1]
                    imports = ' '.join(parts[3:])
                    
                    # Convert ..module to absolute import
                    absolute_path = relative_path.replace('..', '').lstrip('.')
                    suggested = f"from {absolute_path} import {imports}"
                    
                    issues.append(f"Line {line_num}: Replace '{line}' with '{suggested}' for better module compatibility")
        
        return issues

    def _is_function_imported(self, function: str, code: str) -> bool:
        """Check if a function is imported through any import statement"""
        import_lines = [line.strip() for line in code.splitlines() 
                       if line.strip().startswith(('import ', 'from '))]
        
        return any(function in line for line in import_lines)