"""Tests for CLI functionality."""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile

from blueprints.cli.main import main


class TestCLI:
    """Test CLI commands."""

    def test_main_help(self):
        """Test main help command."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Blueprints.md" in result.output
        assert "validate" in result.output
        assert "generate" in result.output
        assert "discover" in result.output
        assert "init" in result.output

    def test_version(self):
        """Test version option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_init_command(self):
        """Test init command creates blueprint file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            result = runner.invoke(
                main, ["init", "test_module", "--output", str(tmp_path)]
            )
            assert result.exit_code == 0
            assert "Created blueprint file" in result.output

            blueprint_file = tmp_path / "test_module.md"
            assert blueprint_file.exists()
            content = blueprint_file.read_text()
            assert "# module: test_module" in content
            assert "## Description" in content
            assert "## Dependencies" in content
            assert "## Components" in content

    def test_validate_command(self):
        """Test validate command."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a test blueprint
            blueprint_file = tmp_path / "test.md"
            blueprint_file.write_text("# module: test\n\n## Description\nTest module")

            result = runner.invoke(main, ["validate", str(blueprint_file)])
            assert result.exit_code == 0
            assert "is valid" in result.output

    def test_generate_command(self):
        """Test generate command."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a test blueprint
            blueprint_file = tmp_path / "test.md"
            blueprint_file.write_text("# module: test\n\n## Description\nTest module")

            result = runner.invoke(main, ["generate", str(blueprint_file)])
            assert result.exit_code == 0
            assert "Generated code" in result.output

    def test_discover_command(self):
        """Test discover command."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create test blueprints
            (tmp_path / "test1.md").write_text("# module: test1")
            (tmp_path / "test2.md").write_text("# module: test2")
            (tmp_path / "README.md").write_text("# README")  # Should be ignored

            result = runner.invoke(main, ["discover", str(tmp_path)])
            assert result.exit_code == 0
            assert "Found 2 blueprint files" in result.output
            assert "test1.md" in result.output
            assert "test2.md" in result.output
            assert "README.md" not in result.output

    def test_discover_no_blueprints(self):
        """Test discover command with no blueprints."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            result = runner.invoke(main, ["discover", str(tmp_path)])
            assert result.exit_code == 0
            assert "No blueprint files found" in result.output

    def test_verbose_flag(self):
        """Test verbose flag."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            blueprint_file = tmp_path / "test.md"
            blueprint_file.write_text("# module: test")

            result = runner.invoke(main, ["--verbose", "validate", str(blueprint_file)])
            assert result.exit_code == 0
            assert "Validating blueprint file" in result.output
