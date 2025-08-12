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

    def parse_project_dependencies(
        self, main_md_path: Optional[Path] = None
    ) -> Dict[str, DependencyInfo]:
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

    def setup_verification_environment(
        self, imports: List[str], temp_dir: Path
    ) -> Dict[str, Path]:
        mocks = {}
        for imp in imports:
            if not self.is_standard_library(imp) and not self.is_expected_dependency(
                imp
            ):
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
        match = re.match(
            r"-\s+([a-zA-Z0-9_.-]+)(?:[><=!]+([0-9.]+[a-zA-Z0-9.]*))?\s*(?:#.*)?", line
        )
        if match:
            name, version = match.groups()
            # Handle package names with extras like "uvicorn[standard]"
            base_name = name.split("[")[0]
            return DependencyInfo(
                name=base_name, version=version, is_third_party=True, is_expected=True
            )
        return None

