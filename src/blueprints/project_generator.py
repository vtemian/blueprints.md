"""Project-level code generation coordination and file management."""

from pathlib import Path
from typing import Dict, List, Optional
import click

from .parser import Blueprint
from .resolver import ResolvedBlueprint
from .code_generator import CodeGenerator


class ProjectGenerator:
    """Coordinates project-level generation across multiple blueprints."""

    def __init__(self, code_generator: CodeGenerator):
        """Initialize with a code generator instance."""
        self.code_generator = code_generator

    def generate_project(
        self,
        resolved: ResolvedBlueprint,
        output_dir: Path,
        language: str = "python",
        force: bool = False,
        main_md_path: Optional[Path] = None,
        verify: bool = True,
    ) -> Dict[str, Path]:
        """Generate code for all blueprints in dependency order."""
        output_dir.mkdir(parents=True, exist_ok=True)

        dependency_versions = self._extract_dependency_versions_safe(main_md_path)
        generated_files = {}
        generated_context = {}

        for blueprint in resolved.generation_order:
            try:
                code, output_path = self._generate_single_blueprint_file(
                    blueprint,
                    resolved,
                    dependency_versions,
                    language,
                    output_dir,
                    force,
                    verify,
                    main_md_path,
                    generated_context,
                )
                generated_files[blueprint.module_name] = output_path
                generated_context[blueprint.module_name] = code
            except Exception as e:
                raise RuntimeError(
                    f"Failed to generate code for {blueprint.module_name}: {str(e)}"
                )

        if language.lower() == "python":
            init_files = self._create_python_init_files(generated_files, force)
            generated_files.update(init_files)

        makefile_path = self._generate_project_makefile(
            resolved, main_md_path, language, force
        )
        if makefile_path:
            generated_files["Makefile"] = makefile_path

        return generated_files

    def generate_single_with_context(
        self,
        resolved: ResolvedBlueprint,
        output_path: Path,
        language: str = "python",
        force: bool = False,
        verify: bool = True,
    ) -> Path:
        """Generate a single file with all dependencies as context in one API call."""
        context_parts = self.code_generator.create_comprehensive_context(resolved, language)

        dependency_versions = {}
        if resolved.main.file_path:
            project_root = resolved.main.file_path.parent
            main_md_path = self.code_generator.find_main_md_in_project(project_root)
            if main_md_path:
                dependency_versions = self.code_generator.extract_dependency_versions(main_md_path)

        try:
            if verify:
                project_root = (
                    resolved.main.file_path.parent
                    if resolved.main.file_path
                    else output_path.parent
                )
                main_md_for_verification = self.code_generator.find_main_md_in_project(project_root)

                code, verification_results = self.code_generator.generate_with_verification(
                    resolved.main,
                    context_parts,
                    language,
                    max_retries=2,
                    project_root=project_root,
                    main_md_path=main_md_for_verification,
                )
                self._log_verification_warnings(resolved.main.module_name, verification_results)
            else:
                code = self.code_generator.generate_single_blueprint(
                    resolved.main, context_parts, language, dependency_versions
                )

            if output_path.exists() and not force:
                if not click.confirm(f"File {output_path} already exists. Overwrite?"):
                    raise RuntimeError("Generation cancelled by user")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(code)

            return output_path

        except Exception as e:
            raise RuntimeError(
                f"Failed to generate code for {resolved.main.module_name}: {str(e)}"
            )

    def _generate_single_blueprint_file(
        self,
        blueprint: Blueprint,
        resolved: ResolvedBlueprint,
        dependency_versions: Dict[str, str],
        language: str,
        output_dir: Path,
        force: bool,
        verify: bool,
        main_md_path: Optional[Path],
        generated_context: Dict[str, str],
    ) -> tuple[str, Path]:
        """Generate code for a single blueprint and return code and output path."""
        context_parts = self.code_generator.create_blueprint_context(
            blueprint, resolved, generated_context, language
        )

        code = self._generate_code_with_verification(
            blueprint, context_parts, language, verify, main_md_path
        )

        output_path = self.code_generator.determine_output_path(blueprint, output_dir, language)
        self.code_generator.save_generated_code(code, output_path, force)

        return code, output_path

    def _generate_code_with_verification(
        self,
        blueprint: Blueprint,
        context_parts: List[str],
        language: str,
        verify: bool,
        main_md_path: Optional[Path],
    ) -> str:
        """Generate code for blueprint with optional verification."""
        if not verify:
            return self.code_generator.generate_single_blueprint(blueprint, context_parts, language)

        project_root = blueprint.file_path.parent if blueprint.file_path else Path.cwd()
        code, verification_results = self.code_generator.generate_with_verification(
            blueprint,
            context_parts,
            language,
            max_retries=2,
            project_root=project_root,
            main_md_path=main_md_path,
        )

        self._log_verification_warnings(blueprint.module_name, verification_results)
        return code

    def _extract_dependency_versions_safe(
        self, main_md_path: Optional[Path]
    ) -> Dict[str, str]:
        """Safely extract dependency versions from main.md."""
        if not main_md_path or not main_md_path.exists():
            return {}
        return self.code_generator.extract_dependency_versions(main_md_path)

    def _log_verification_warnings(
        self, module_name: str, verification_results: List
    ) -> None:
        """Log any verification warnings."""
        failed_verifications = [r for r in verification_results if not r.success]
        if failed_verifications:
            print(f"Warning: Blueprint {module_name} has verification issues:")
            for result in failed_verifications:
                print(f"  - {result.error_type}: {result.error_message}")

    def _create_python_init_files(
        self, generated_files: Dict[str, Path], force: bool = False
    ) -> Dict[str, Path]:
        """Create __init__.py files in all directories containing Python files."""
        init_files = {}

        python_dirs = set()
        for module_name, file_path in generated_files.items():
            if file_path.suffix == ".py":
                python_dirs.add(file_path.parent)

        for dir_path in python_dirs:
            init_path = dir_path / "__init__.py"

            if init_path in generated_files.values():
                continue

            if not init_path.exists() or force:
                init_path.write_text("")
                module_key = f"{dir_path.name}.__init__"
                init_files[module_key] = init_path

        return init_files

    def _generate_project_makefile(
        self,
        resolved: ResolvedBlueprint,
        main_md_path: Optional[Path],
        language: str,
        force: bool,
    ) -> Optional[Path]:
        """Generate project Makefile."""
        project_root = self._find_project_root(resolved, main_md_path)
        return MakefileGenerator().generate_makefile(
            resolved, project_root, language, force, main_md_path
        )

    def _find_project_root(
        self, resolved: ResolvedBlueprint, main_md_path: Optional[Path] = None
    ) -> Path:
        """Find the project root directory by looking for main.md."""
        if main_md_path:
            return main_md_path.parent

        for blueprint in resolved.generation_order:
            if blueprint.file_path and blueprint.file_path.name == "main.md":
                return blueprint.file_path.parent

        if resolved.main.file_path:
            return resolved.main.file_path.parent

        return Path.cwd()


class MakefileGenerator:
    """Generates Makefiles for projects based on blueprint specifications."""

    def generate_makefile(
        self,
        resolved: ResolvedBlueprint,
        output_dir: Path,
        language: str,
        force: bool,
        main_md_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Generate a Makefile with project setup and run commands."""
        main_md_blueprint = self._find_main_blueprint(resolved, main_md_path)
        setup_blueprint = main_md_blueprint if main_md_blueprint else resolved.main

        app_module = self._find_app_module(resolved)

        project_info = self._extract_project_info(setup_blueprint)
        makefile_content = self._create_makefile_content(
            setup_blueprint.module_name,
            project_info,
            language,
            app_module,
        )

        if not makefile_content.strip():
            return None

        makefile_path = output_dir / "Makefile"

        if makefile_path.exists() and not force:
            return None

        makefile_path.write_text(makefile_content)
        return makefile_path

    def _find_main_blueprint(self, resolved: ResolvedBlueprint, main_md_path: Optional[Path]):
        """Find the main.md blueprint for project setup info."""
        if main_md_path and main_md_path.exists():
            from .parser import BlueprintParser
            parser = BlueprintParser()
            return parser.parse_file(main_md_path)

        for blueprint in resolved.generation_order:
            if blueprint.file_path and blueprint.file_path.name == "main.md":
                return blueprint

        return None

    def _find_app_module(self, resolved: ResolvedBlueprint) -> Optional[str]:
        """Find the actual app entrypoint module."""
        for blueprint in resolved.generation_order:
            if blueprint.file_path and blueprint.file_path.name == "app.md":
                return blueprint.file_path.stem

        if resolved.main.file_path:
            return resolved.main.file_path.stem

        return None

    def _extract_project_info(self, setup_blueprint: Blueprint) -> Dict:
        """Extract project setup information from blueprint content."""
        info = {
            "dependencies": [],
            "dev_dependencies": [],
            "install_commands": [],
            "run_commands": [],
            "env_vars": [],
        }

        content_lines = setup_blueprint.raw_content.split("\n")
        current_section = None

        for line in content_lines:
            line = line.strip()

            if self._is_section_header(line):
                current_section = self._identify_section(line)
                continue

            if current_section and line.startswith("- "):
                self._process_section_line(line, current_section, info)
            elif current_section == "installation" and self._is_command_line(line):
                info["install_commands"].append(line)
            elif current_section == "installation" and line.startswith("export"):
                info["env_vars"].append(line)
            elif current_section == "running" and self._is_run_command(line):
                info["run_commands"].append(line)

        return info

    def _is_section_header(self, line: str) -> bool:
        """Check if line is a section header."""
        return (line.startswith("##") or line.startswith("# ") or 
                (line.endswith(":") and not line.startswith("-")))

    def _identify_section(self, line: str) -> Optional[str]:
        """Identify which section type this header represents."""
        line_lower = line.lower()
        if ("third-party dependencies" in line_lower or "dependencies:" in line_lower or 
            "dependencies to install:" in line_lower):
            return "dependencies"
        elif "development dependencies" in line_lower:
            return "dev_dependencies"
        elif "installation" in line_lower:
            return "installation"
        elif "running" in line_lower:
            return "running"
        return None

    def _is_command_line(self, line: str) -> bool:
        """Check if line contains installation commands."""
        return (line.startswith("pip install") or line.startswith("uv") or 
                line.startswith("npm"))

    def _is_run_command(self, line: str) -> bool:
        """Check if line contains run commands."""
        return (line.startswith("uvicorn") or line.startswith("python") or 
                line.startswith("npm") or line.startswith("node"))

    def _process_section_line(self, line: str, section: str, info: Dict) -> None:
        """Process a line within a specific section."""
        content = line[2:].split("#")[0].strip()  # Remove "- " and comments
        if " - " in content:
            content = content.split(" - ")[0].strip()  # Handle new format
        if content and section in info:
            info[section].append(content)

    def _create_makefile_content(
        self,
        project_name: str,
        project_info: Dict,
        language: str,
        app_module: Optional[str] = None,
    ) -> str:
        """Create Makefile content based on project information."""
        lines = [
            f"# Makefile for {project_name}",
            f"# Generated by blueprints.md",
            "",
            ".PHONY: help install install-dev setup run dev test clean",
            "",
            "help:",
            "\t@echo 'Available commands:'",
            "\t@echo '  install     - Install production dependencies'",
            "\t@echo '  install-dev - Install development dependencies'",
            "\t@echo '  setup       - Complete project setup'",
            "\t@echo '  run         - Run the application'",
            "\t@echo '  dev         - Run in development mode'",
            "\t@echo '  test        - Run tests'",
            "\t@echo '  clean       - Clean up generated files'",
            "",
        ]

        self._add_requirements_generation(lines, project_info)
        self._add_install_commands(lines, project_info, language)
        self._add_setup_command(lines, project_info)
        self._add_run_commands(lines, project_info, language, project_name, app_module)
        self._add_test_command(lines, language)
        self._add_clean_command(lines, language)

        return "\n".join(lines)

    def _add_requirements_generation(self, lines: List[str], project_info: Dict) -> None:
        """Add requirements file generation targets."""
        if project_info["dependencies"]:
            lines.extend([
                "requirements.txt:",
                "\t@echo 'Generating requirements.txt...'",
                "\t@echo '# Production dependencies' > requirements.txt",
            ])
            for dep in project_info["dependencies"]:
                lines.append(f"\t@echo '{dep}' >> requirements.txt")
            lines.append("")

        if project_info["dev_dependencies"]:
            lines.extend([
                "requirements-dev.txt:",
                "\t@echo 'Generating requirements-dev.txt...'",
                "\t@echo '# Development dependencies' > requirements-dev.txt",
            ])
            for dep in project_info["dev_dependencies"]:
                lines.append(f"\t@echo '{dep}' >> requirements-dev.txt")
            lines.append("")

    def _add_install_commands(self, lines: List[str], project_info: Dict, language: str) -> None:
        """Add installation commands."""
        if language.lower() == "python":
            if project_info["dependencies"]:
                lines.extend([
                    "install: requirements.txt",
                    "\t@echo 'Installing production dependencies...'",
                    "\tpip install -r requirements.txt",
                    "",
                ])

            if project_info["dev_dependencies"]:
                lines.extend([
                    "install-dev: requirements-dev.txt",
                    "\t@echo 'Installing development dependencies...'",
                    "\tpip install -r requirements-dev.txt",
                    "",
                ])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend([
                "install:",
                "\t@echo 'Installing dependencies...'",
                "\tnpm install",
                "",
                "install-dev:",
                "\t@echo 'Installing development dependencies...'",
                "\tnpm install --include=dev",
                "",
            ])

    def _add_setup_command(self, lines: List[str], project_info: Dict) -> None:
        """Add setup command."""
        setup_deps = []
        if project_info["dependencies"]:
            setup_deps.append("install")
        if project_info["dev_dependencies"]:
            setup_deps.append("install-dev")

        if setup_deps:
            lines.extend([
                f"setup: {' '.join(setup_deps)}",
                "\t@echo 'Project setup complete!'",
                "\t@echo 'Environment variables to set:'",
            ])
            for env_var in project_info["env_vars"]:
                lines.append(f"\t@echo '  {env_var}'")
            lines.append("")

    def _add_run_commands(
        self, 
        lines: List[str], 
        project_info: Dict, 
        language: str, 
        project_name: str,
        app_module: Optional[str]
    ) -> None:
        """Add run commands."""
        if project_info["run_commands"]:
            prod_cmd = project_info["run_commands"][0]
            dev_cmd = (project_info["run_commands"][1] 
                      if len(project_info["run_commands"]) > 1 
                      else prod_cmd)

            if prod_cmd:
                lines.extend(["run:", "\t@echo 'Starting application...'", f"\t{prod_cmd}", ""])

            if dev_cmd:
                lines.extend(["dev:", "\t@echo 'Starting development server...'", f"\t{dev_cmd}", ""])
        else:
            self._add_default_run_commands(lines, language, project_name, app_module)

    def _add_default_run_commands(
        self, lines: List[str], language: str, project_name: str, app_module: Optional[str]
    ) -> None:
        """Add default run commands based on language."""
        if language.lower() == "python":
            module_to_run = app_module if app_module else project_name
            lines.extend([
                "run:",
                f"\t@echo 'Starting {module_to_run}...'",
                f"\tpython -m {module_to_run}",
                "",
                "dev:",
                f"\t@echo 'Starting {module_to_run} in development mode...'",
                f"\tpython -m {module_to_run} --reload",
                "",
            ])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend([
                "run:",
                "\t@echo 'Starting application...'",
                "\tnpm start",
                "",
                "dev:",
                "\t@echo 'Starting development server...'",
                "\tnpm run dev",
                "",
            ])

    def _add_test_command(self, lines: List[str], language: str) -> None:
        """Add test command."""
        if language.lower() == "python":
            lines.extend(["test:", "\t@echo 'Running tests...'", "\tpytest", ""])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend(["test:", "\t@echo 'Running tests...'", "\tnpm test", ""])

    def _add_clean_command(self, lines: List[str], language: str) -> None:
        """Add clean command."""
        if language.lower() == "python":
            lines.extend([
                "clean:",
                "\t@echo 'Cleaning up...'",
                "\tfind . -type f -name '*.pyc' -delete",
                "\tfind . -type d -name '__pycache__' -delete",
                "\trm -f requirements.txt requirements-dev.txt",
                "",
            ])
        elif language.lower() in ["javascript", "typescript"]:
            lines.extend([
                "clean:",
                "\t@echo 'Cleaning up...'",
                "\trm -rf node_modules",
                "\trm -f package-lock.json",
                "",
            ])