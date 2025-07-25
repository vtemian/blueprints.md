from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import ast
import importlib
import importlib.util
import importlib.machinery
import tempfile
import sys
import subprocess
import re

@dataclass
class VerificationResult:
    """Result of a code verification check"""
    success: bool
    error_type: Optional[str] = None  # "syntax", "import", "type", "runtime"
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

class CodeVerifier:
    """Verifies code quality and functionality"""

    def __init__(self, language: str = "python", project_root: Optional[Path] = None):
        self.language = language
        self.project_root = project_root or Path.cwd()
        
        # Initialize smart dependency manager
        try:
            from .dependency_manager import DependencyManager, SmartVerifier
            self.dependency_manager = DependencyManager(self.project_root)
            self.smart_verifier = SmartVerifier(self.dependency_manager, language)
            self.smart_imports_enabled = True
        except ImportError:
            self.smart_imports_enabled = False

    def verify_syntax(self, code: str) -> VerificationResult:
        """Check if code can be parsed"""
        try:
            ast.parse(code)
            return VerificationResult(success=True)
        except SyntaxError as e:
            return VerificationResult(
                success=False,
                error_type="syntax",
                error_message=str(e),
                error_line=e.lineno
            )

    def verify_imports(self, code: str, project_root: Path, main_md_path: Optional[Path] = None) -> VerificationResult:
        """Check import resolution with smart dependency management"""
        if self.smart_imports_enabled:
            # Use smart verification that understands project dependencies
            if main_md_path:
                self.dependency_manager.parse_project_dependencies(main_md_path)
            
            result = self.smart_verifier.verify_imports_smart(code, project_root)
            
            if result.success:
                return VerificationResult(success=True)
            else:
                return VerificationResult(
                    success=False,
                    error_type="import",
                    error_message="; ".join(result.errors),
                    warnings=[f"Using smart dependency verification"]
                )
        else:
            # Fallback to basic import checking
            imports = self._extract_imports(code)
            for imp in imports:
                if not self._check_import_availability(imp, project_root):
                    return VerificationResult(
                        success=False,
                        error_type="import",
                        error_message=f"Could not resolve import: {imp}"
                    )
            return VerificationResult(success=True)

    def verify_types(self, code: str, file_path: Path) -> VerificationResult:
        """Type checking with mypy"""
        try:
            import mypy.api
            return self._run_mypy_check(file_path)
        except ImportError:
            return VerificationResult(success=True, warnings=["mypy not available for type checking"])

    def verify_runtime(self, code: str, file_path: Path) -> VerificationResult:
        """Basic runtime check"""
        try:
            with open(file_path, 'w') as f:
                f.write(code)
            importlib.machinery.SourceFileLoader(
                file_path.stem,
                str(file_path)
            ).load_module()
            return VerificationResult(success=True)
        except Exception as e:
            return VerificationResult(
                success=False,
                error_type="runtime",
                error_message=str(e)
            )

    def verify_all(self, code: str, file_path: Path, project_root: Path, main_md_path: Optional[Path] = None, blueprint: Optional['Blueprint'] = None) -> List[VerificationResult]:
        """Run all verifications"""
        results = []
        results.append(self.verify_syntax(code))
        if not results[-1].success:
            return results

        results.append(self.verify_imports(code, project_root, main_md_path))
        if not results[-1].success:
            return results

        # Add blueprint dependency verification if blueprint is provided
        if blueprint:
            results.append(self.verify_blueprint_dependencies(code, blueprint))
            if not results[-1].success:
                return results

        # Add missing third-party imports check 
        results.append(self.verify_third_party_imports(code))
        if not results[-1].success:
            return results

        # Add async/await verification
        results.append(self.verify_async_await_usage(code, blueprint))
        if not results[-1].success:
            return results

        results.append(self.verify_types(code, file_path))
        if not results[-1].success:
            return results

        results.append(self.verify_runtime(code, file_path))
        return results

    def verify_blueprint_dependencies(self, code: str, blueprint: 'Blueprint') -> VerificationResult:
        """Verify that code imports match blueprint dependencies."""
        if not blueprint.blueprint_refs:
            return VerificationResult(success=True)
            
        expected_imports = self._extract_expected_imports_from_refs(blueprint.blueprint_refs, blueprint.module_name)
        actual_imports = self._extract_actual_imports(code)
        
        errors = []
        
        # Check that all expected imports are present with correct aliases
        for expected in expected_imports:
            if not self._import_matches(expected, actual_imports):
                errors.append(f"Missing or incorrect import: expected '{expected['statement']}' but found mismatched import")
        
        # Check for unexpected relative imports that should be absolute
        for actual in actual_imports:
            if self._has_relative_import(actual):
                errors.append(f"Relative import found: '{actual}' - top-level modules should use absolute imports matching blueprint dependencies")
        
        if errors:
            return VerificationResult(
                success=False,
                error_type="blueprint_dependencies", 
                error_message="; ".join(errors)
            )
        
        return VerificationResult(success=True)
    
    def verify_third_party_imports(self, code: str) -> VerificationResult:
        """Verify that commonly used third-party functions have their imports."""
        # Common third-party functions that are often used without imports
        function_to_import = {
            # SQLAlchemy
            'create_engine': 'from sqlalchemy import create_engine',
            'sessionmaker': 'from sqlalchemy.orm import sessionmaker', 
            'declarative_base': 'from sqlalchemy.orm import declarative_base',
            'Session': 'from sqlalchemy.orm import Session',
            'Column': 'from sqlalchemy import Column',
            'Integer': 'from sqlalchemy import Integer',
            'String': 'from sqlalchemy import String',
            'Boolean': 'from sqlalchemy import Boolean',
            'DateTime': 'from sqlalchemy import DateTime',
            'ForeignKey': 'from sqlalchemy import ForeignKey',
            'relationship': 'from sqlalchemy.orm import relationship',
            # FastAPI
            'FastAPI': 'from fastapi import FastAPI',
            'APIRouter': 'from fastapi import APIRouter',
            'Depends': 'from fastapi import Depends',
            'HTTPException': 'from fastapi import HTTPException',
            'status': 'from fastapi import status',
            'Query': 'from fastapi import Query',
            # Pydantic
            'BaseModel': 'from pydantic import BaseModel',
            'Field': 'from pydantic import Field',
        }
        
        # Extract existing imports
        existing_imports = set()
        import_lines = []
        for line in code.splitlines():
            if line.strip().startswith(('import ', 'from ')):
                import_lines.append(line.strip())
                # Extract imported names
                if ' import ' in line:
                    import_part = line.split(' import ')[1]
                    for name in import_part.replace(' as ', ',').split(','):
                        existing_imports.add(name.strip())
        
        # Check for missing imports
        missing_imports = []
        for function, import_statement in function_to_import.items():
            if function in code and function not in existing_imports:
                # Check if it's not already imported with a different pattern
                function_imported = any(function in imp for imp in import_lines)
                if not function_imported:
                    missing_imports.append(f"Function '{function}' is used but not imported. Add: {import_statement}")
        
        if missing_imports:
            return VerificationResult(
                success=False,
                error_type="missing_imports",
                error_message="; ".join(missing_imports)
            )
        
        return VerificationResult(success=True)
    
    def verify_async_await_usage(self, code: str, blueprint: Optional['Blueprint'] = None) -> VerificationResult:
        """Verify that async/await usage matches function definitions using Claude."""
        # Skip async/await verification for now - it will be handled by Claude during generation
        # This prevents hardcoding of function signatures
        return VerificationResult(success=True)
    
    def _extract_expected_imports_from_refs(self, blueprint_refs: List['BlueprintReference'], current_module: Optional[str] = None) -> List[dict]:
        """Extract expected import statements from blueprint references."""
        expected = []
        for ref in blueprint_refs:
            # Handle both @.module and .module formats (parser may strip @)
            module_path = ref.module_path
            if module_path.startswith('..'):
                # Remove double dots for absolute import (from parent directory)
                module_path = module_path[2:]
            elif module_path.startswith('.'):
                # Single dot - sibling module in same namespace
                if current_module and '.' in current_module:
                    # Get parent namespace and append the sibling module
                    parent_namespace = '.'.join(current_module.split('.')[:-1])
                    sibling_module = module_path[1:]  # Remove the dot
                    module_path = f"{parent_namespace}.{sibling_module}"
                else:
                    # Remove leading dot for absolute import (fallback)
                    module_path = module_path[1:]
            
            for item in ref.items:
                if ' as ' in item:
                    orig_item, alias = item.split(' as ')
                    statement = f"from {module_path} import {orig_item.strip()} as {alias.strip()}"
                    expected.append({
                        'module': module_path,
                        'item': orig_item.strip(),
                        'alias': alias.strip(),
                        'statement': statement
                    })
                else:
                    statement = f"from {module_path} import {item.strip()}"
                    expected.append({
                        'module': module_path,
                        'item': item.strip(),
                        'alias': None,
                        'statement': statement
                    })
        
        return expected
    
    def _extract_expected_imports(self, dependencies: List[str]) -> List[dict]:
        """Extract expected import statements from blueprint dependencies."""
        expected = []
        for dep in dependencies:
            # Parse blueprint dependency format: @.api.tasks[router as tasks_router]
            if '[' in dep and ']' in dep:
                # Extract module and import details
                module_part = dep.split('[')[0].replace('@.', '').replace('@', '')
                import_part = dep.split('[')[1].split(']')[0]
                
                if ' as ' in import_part:
                    item, alias = import_part.split(' as ')
                    statement = f"from {module_part} import {item.strip()} as {alias.strip()}"
                else:
                    statement = f"from {module_part} import {import_part.strip()}"
                
                expected.append({
                    'module': module_part,
                    'item': import_part.split(' as ')[0].strip() if ' as ' in import_part else import_part.strip(),
                    'alias': import_part.split(' as ')[1].strip() if ' as ' in import_part else None,
                    'statement': statement
                })
        
        return expected
    
    def _extract_actual_imports(self, code: str) -> List[str]:
        """Extract actual import statements from code."""
        import re
        imports = []
        
        for line in code.splitlines():
            line = line.strip()
            # Match both 'from X import Y' and 'import X' patterns
            if re.match(r'^(from\s+[\w.]+\s+import\s+.+|import\s+[\w.]+)', line):
                imports.append(line)
        
        return imports
    
    def _import_matches(self, expected: dict, actual_imports: List[str]) -> bool:
        """Check if expected import matches any actual import."""
        expected_statement = expected['statement']
        
        # Try exact match first
        if expected_statement in actual_imports:
            return True
            
        # Try variations (different whitespace, order, etc.)
        for actual in actual_imports:
            if self._normalize_import(expected_statement) == self._normalize_import(actual):
                return True
                
        return False
    
    def _normalize_import(self, import_statement: str) -> str:
        """Normalize import statement for comparison."""
        # Remove extra whitespace and standardize format
        import re
        normalized = re.sub(r'\s+', ' ', import_statement.strip())
        return normalized
    
    def _has_relative_import(self, import_statement: str) -> bool:
        """Check if import statement contains relative imports."""
        import re
        # Match patterns like "from .module import ..." or "from ..module import ..."
        return bool(re.search(r'from\s+\.+\w', import_statement))
    
    def _is_expected_relative_import(self, actual_import: str, expected_imports: List[dict]) -> bool:
        """Check if a relative import is expected based on blueprint dependencies."""
        # This is a placeholder - in practice, relative imports should be converted to absolute
        # based on the blueprint dependencies
        return False

    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements"""
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module)
        except:
            pass
        return imports

    def _check_import_availability(self, import_name: str, project_root: Path) -> bool:
        """Check if import exists"""
        try:
            if import_name in sys.modules:
                return True
            importlib.import_module(import_name)
            return True
        except ImportError:
            try:
                spec = importlib.util.find_spec(import_name, [str(project_root)])
                return spec is not None
            except:
                return False

    def _run_mypy_check(self, file_path: Path) -> VerificationResult:
        """Run mypy type checking"""
        try:
            import mypy.api
            stdout, stderr, exit_code = mypy.api.run([str(file_path)])
            if exit_code == 0:
                return VerificationResult(success=True)
            return VerificationResult(
                success=False,
                error_type="type",
                error_message=stdout or stderr
            )
        except ImportError:
            return VerificationResult(success=True, warnings=["mypy not available for type checking"])

    def _create_temp_file(self, code: str, suffix: str = ".py") -> Path:
        """Create temporary file for verification"""
        tmp = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False
        )
        tmp_path = Path(tmp.name)
        with tmp:
            tmp.write(code)
        return tmp_path

class GenerationVerifier:
    """Verifies and improves generated code"""

    def __init__(self, max_retries: int = 3, language: str = "python", project_root: Optional[Path] = None):
        self.max_retries = max_retries
        self.project_root = project_root or Path.cwd()
        self.verifier = CodeVerifier(language, project_root)

    def verify_and_improve(
        self,
        generator: 'CodeGenerator',
        blueprint: 'Blueprint',
        context_parts: List[str],
        language: str,
        main_md_path: Optional[Path] = None
    ) -> Tuple[str, List[VerificationResult]]:
        """Main verification loop"""
        # Extract dependency versions if available
        dependency_versions = {}
        if main_md_path and main_md_path.exists():
            dependency_versions = generator._extract_dependency_versions(main_md_path)
        
        code = generator.generate_single_blueprint(blueprint, context_parts, language, dependency_versions)
        tmp_file = self.verifier._create_temp_file(code)

        # Find main.md if not provided
        if main_md_path is None:
            potential_main = self.project_root / "main.md"
            if potential_main.exists():
                main_md_path = potential_main

        for attempt in range(self.max_retries):
            results = self.verifier.verify_all(
                code,
                tmp_file,
                self.project_root,
                main_md_path,
                blueprint
            )
            
            if all(r.success for r in results):
                return code, results

            retry_prompt = self._create_retry_prompt(
                blueprint,
                context_parts,
                code,
                results,
                attempt,
                language
            )
            code = generator.generate_single_blueprint(blueprint, [retry_prompt], language, dependency_versions)
            
        return code, results

    def _create_retry_prompt(
        self,
        blueprint: 'Blueprint',
        context_parts: List[str],
        previous_code: str,
        verification_results: List[VerificationResult],
        attempt: int,
        language: str
    ) -> str:
        """Create improved prompt based on errors"""
        error_feedback = self._format_error_feedback(verification_results)
        blueprint_deps = self._format_blueprint_dependencies(blueprint)
        
        return f"""Previous generation attempt {attempt + 1} failed with errors:
{error_feedback}

IMPORTANT: The code must match the blueprint dependencies exactly:
{blueprint_deps}

Original context:
{' '.join(context_parts)}

Previous code:
{previous_code}

Please fix the errors and regenerate the code in {language}. Pay special attention to:
1. Import statements must match the blueprint dependencies exactly
2. Use the correct module paths and aliases as specified in the blueprint
3. Avoid relative imports unless explicitly specified in the blueprint"""

    def _format_blueprint_dependencies(self, blueprint: 'Blueprint') -> str:
        """Format blueprint dependencies for retry prompt."""
        if not blueprint.blueprint_refs:
            return "No specific dependencies declared."
            
        formatted = []
        for ref in blueprint.blueprint_refs:
            # Handle both @.module and .module formats (parser may strip @)
            module_path = ref.module_path
            if module_path.startswith('..'):
                # Remove double dots for absolute import (from parent directory)
                module_path = module_path[2:]
            elif module_path.startswith('.'):
                # Single dot - sibling module in same namespace
                if blueprint.module_name and '.' in blueprint.module_name:
                    # Get parent namespace and append the sibling module
                    parent_namespace = '.'.join(blueprint.module_name.split('.')[:-1])
                    sibling_module = module_path[1:]  # Remove the dot
                    module_path = f"{parent_namespace}.{sibling_module}"
                else:
                    # Remove leading dot for absolute import (fallback)
                    module_path = module_path[1:]
            
            for item in ref.items:
                if ' as ' in item:
                    orig_item, alias = item.split(' as ')
                    expected_import = f"from {module_path} import {orig_item.strip()} as {alias.strip()}"
                    formatted.append(f"- {ref.module_path}[{item}] → {expected_import}")
                else:
                    expected_import = f"from {module_path} import {item.strip()}"
                    formatted.append(f"- {ref.module_path}[{item}] → {expected_import}")
        
        return "\n".join(formatted)
    
    def _format_error_feedback(self, results: List[VerificationResult]) -> str:
        """Format verification errors for prompt"""
        feedback = []
        for result in results:
            if not result.success:
                error = f"Error type: {result.error_type}\n"
                if result.error_message:
                    # Special formatting for missing imports
                    if result.error_type == "missing_imports":
                        error += "Missing third-party imports:\n"
                        for missing in result.error_message.split('; '):
                            error += f"  - {missing}\n"
                    else:
                        error += f"Message: {result.error_message}\n"
                if result.error_line:
                    error += f"Line: {result.error_line}\n"
                feedback.append(error)
        return "\n".join(feedback)