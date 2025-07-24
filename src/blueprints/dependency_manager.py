from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set
import importlib
import os
import re
import sys
import tempfile

@dataclass
class DependencyInfo:
    """Information about a code dependency."""
    name: str
    version: Optional[str] = None
    is_standard_library: bool = False
    is_third_party: bool = False 
    is_local: bool = False
    is_expected: bool = False  # Known from main.md dependencies

class ImportCategory(Enum):
    """Categories for import statements."""
    STANDARD_LIBRARY = auto()
    THIRD_PARTY = auto()
    LOCAL = auto()
    UNKNOWN = auto()

@dataclass
class VerificationResult:
    """Result of import verification."""
    success: bool
    errors: List[str]

class DependencyManager:
    """Manages project dependencies and import verification."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.expected_dependencies: Dict[str, DependencyInfo] = {}
        self.stdlib_modules = self._get_stdlib_modules()

    def parse_project_dependencies(self, main_md_path: Optional[Path] = None) -> Dict[str, DependencyInfo]:
        if main_md_path is None:
            main_md_path = self.project_root / "main.md"
        
        if not main_md_path.exists():
            return {}

        content = main_md_path.read_text()
        deps = self._extract_dependencies_from_main_md(content)
        self.expected_dependencies = {d.name: d for d in deps}
        return self.expected_dependencies

    def categorize_import(self, import_name: str) -> ImportCategory:
        if self.is_standard_library(import_name):
            return ImportCategory.STANDARD_LIBRARY
        elif import_name in self.expected_dependencies:
            return ImportCategory.THIRD_PARTY
        elif (self.project_root / import_name.replace(".", "/")).exists():
            return ImportCategory.LOCAL
        return ImportCategory.UNKNOWN

    def is_standard_library(self, module_name: str) -> bool:
        return module_name in self.stdlib_modules

    def is_expected_dependency(self, import_name: str) -> bool:
        return import_name in self.expected_dependencies

    def create_mock_module(self, module_name: str, temp_dir: Path) -> Path:
        mock_path = temp_dir / f"{module_name}.py"
        mock_path.write_text(f"# Mock module for {module_name}")
        return mock_path

    def setup_verification_environment(self, imports: List[str], temp_dir: Path) -> Dict[str, Path]:
        mocks = {}
        for imp in imports:
            if not self.is_standard_library(imp) and not self.is_expected_dependency(imp):
                mock_path = self.create_mock_module(imp, temp_dir)
                mocks[imp] = mock_path
        return mocks

    def _extract_dependencies_from_main_md(self, content: str) -> List[DependencyInfo]:
        deps = []
        in_third_party = False
        in_dev_deps = False
        
        for line in content.splitlines():
            line = line.strip()
            
            if "## Third-party Dependencies" in line:
                in_third_party = True
                in_dev_deps = False
                continue
            elif "## Development Dependencies" in line:
                in_third_party = False
                in_dev_deps = True
                continue
            elif line.startswith("##") or line.startswith("# "):
                in_third_party = False
                in_dev_deps = False
                continue
            
            if (in_third_party or in_dev_deps) and line.startswith("- "):
                if dep := self._parse_dependency_line(line):
                    deps.append(dep)
        return deps

    def _get_stdlib_modules(self) -> Set[str]:
        stdlib_modules = set(sys.stdlib_module_names)
        return stdlib_modules

    def _parse_dependency_line(self, line: str) -> Optional[DependencyInfo]:
        line = line.strip()
        if not line or line.startswith("#"):
            return None
            
        # Parse format like: "- fastapi>=0.104.0  # Web framework"
        match = re.match(r"-\s+([a-zA-Z0-9_.-]+)(?:[><=!]+([0-9.]+[a-zA-Z0-9.]*))?\s*(?:#.*)?", line)
        if match:
            name, version = match.groups()
            # Handle package names with extras like "uvicorn[standard]"
            base_name = name.split('[')[0]
            return DependencyInfo(
                name=base_name,
                version=version,
                is_third_party=True,
                is_expected=True
            )
        return None

class SmartVerifier:
    """Smart verification of code imports."""

    def __init__(self, dependency_manager: DependencyManager, language: str = "python"):
        self.dependency_manager = dependency_manager
        self.language = language

    def verify_imports_smart(self, code: str, project_root: Path) -> VerificationResult:
        errors = []
        imports = self._extract_imports(code)
        
        for imp in imports:
            category = self.dependency_manager.categorize_import(imp)
            if not self._should_verify_import(imp, category):
                errors.append(self._create_import_error_message(imp, category))

        return VerificationResult(
            success=len(errors) == 0,
            errors=errors
        )

    def _should_verify_import(self, import_name: str, category: ImportCategory) -> bool:
        """Return True if import should pass verification (no error)."""
        if category == ImportCategory.STANDARD_LIBRARY:
            return True  # Standard library imports are always OK
        if category == ImportCategory.THIRD_PARTY:
            return self.dependency_manager.is_expected_dependency(import_name)  # OK if expected
        if category == ImportCategory.LOCAL:
            return True  # Local imports are OK
        return False  # Unknown imports are not OK

    def _create_import_error_message(self, import_name: str, category: ImportCategory) -> str:
        if category == ImportCategory.UNKNOWN:
            return f"Unknown import: {import_name}"
        if category == ImportCategory.THIRD_PARTY and not self.dependency_manager.is_expected_dependency(import_name):
            return f"Unexpected third-party import: {import_name}"
        return f"Invalid import: {import_name}"

    def _extract_imports(self, code: str) -> List[str]:
        imports = []
        import_pattern = r"^\s*(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+))"
        
        for line in code.splitlines():
            match = re.match(import_pattern, line)
            if match:
                module = match.group(1) or match.group(2)
                imports.append(module.split(".")[0])
                
        return imports