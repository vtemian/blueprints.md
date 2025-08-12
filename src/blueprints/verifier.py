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
        """Check for missing imports and relative import issues"""
        logger = get_logger('verifier')
        
        # Check for relative import issues
        relative_import_issues = self._check_relative_imports(code)
        
        # Check for missing imports
        missing = self._find_missing_imports(code)
        
        issues = []
        if relative_import_issues:
            issues.extend(relative_import_issues)
        if missing:
            issues.extend(missing)
        
        if issues:
            logger.debug(f"Import issues found: {len(issues)} total")
            return VerificationResult(
                success=False,
                error_type="import",
                error_message="Import issues found",
                suggestions=issues
            )
        
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
        """Use Claude to analyze what imports are missing"""
        import_request = f"""
Analyze this Python code and identify missing imports:

```python
{code}
```

Return a JSON object with missing import statements:
{{
    "function_name": "import statement",
    "ClassName": "from module import ClassName",
    ...
}}

Only include imports that are clearly missing (function/class used but not imported).
Be thorough and check all used functions, classes, and modules.
"""
        
        try:
            response = self.client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": import_request}]
            )
            
            response_text = response.content[0].text
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
            if json_match:
                import_mappings = json.loads(json_match.group())
                return import_mappings
            
            return {}
            
        except Exception:
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