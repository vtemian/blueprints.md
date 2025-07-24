"""Main CLI entry point for blueprints.md."""

import click
from pathlib import Path
from typing import Optional

from blueprints import __version__
from blueprints.parser import BlueprintParser
from blueprints.generator import CodeGenerator
from blueprints.resolver import BlueprintResolver


@click.group()
@click.version_option(version=__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Blueprints.md - Markdown-to-code generation system."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("blueprint_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def validate(ctx: click.Context, blueprint_file: Path) -> None:
    """Validate a blueprint file."""
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Validating blueprint file: {blueprint_file}")

    # TODO: Implement blueprint validation
    click.echo(f"✓ Blueprint file '{blueprint_file}' is valid")


@main.command()
@click.argument("blueprint_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: same directory as blueprint)",
)
@click.option(
    "--language",
    "-l",
    default="python",
    help="Target programming language (default: python)",
)
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key (can also be set via ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing files without confirmation",
)
@click.pass_context
def generate(ctx: click.Context, blueprint_file: Path, output: Optional[Path], language: str, api_key: Optional[str], force: bool) -> None:
    """Generate source code from a blueprint file using Claude API."""
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Generating code from blueprint: {blueprint_file}")

    try:
        # Resolve blueprint dependencies
        resolver = BlueprintResolver(project_root=blueprint_file.parent.parent if blueprint_file.parent.name != "." else blueprint_file.parent)
        resolved = resolver.resolve(blueprint_file)
        
        if verbose:
            click.echo(f"  Module: {resolved.main.module_name}")
            click.echo(f"  Components: {len(resolved.main.components)}")
            if resolved.dependencies:
                click.echo(f"  Dependencies: {len(resolved.dependencies)} blueprints")
                for dep in resolved.dependencies:
                    click.echo(f"    - {dep.module_name}")
        
        # Generate code using Claude API with dependency context
        generator = CodeGenerator(api_key=api_key)
        
        # Determine output path
        if output is None:
            # Default to same directory as blueprint file
            if resolved.main.file_path:
                blueprint_dir = resolved.main.file_path.parent
                filename = f"{resolved.main.file_path.stem}{generator._get_file_extension(language)}"
                output = blueprint_dir / filename
            else:
                # Fallback
                ext = {
                    "python": ".py",
                    "javascript": ".js", 
                    "typescript": ".ts",
                    "java": ".java",
                    "go": ".go",
                    "rust": ".rs"
                }.get(language.lower(), ".txt")
                output = blueprint_file.parent / f"{blueprint_file.stem}{ext}"
        
        # Generate single file with full dependency context
        output_path = generator.generate_single_with_context(resolved, output, language, force)
        
        click.echo(f"✓ Generated code saved to: {output_path}")
        
        if verbose:
            click.echo(f"  Language: {language}")
            click.echo(f"  Size: {output_path.stat().st_size} bytes")
            
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to generate code: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@main.command()
@click.argument("blueprint_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--language",
    "-l",
    default="python",
    help="Target programming language (default: python)",
)
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key (can also be set via ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing files without confirmation",
)
@click.pass_context
def generate_project(ctx: click.Context, blueprint_file: Path, language: str, api_key: Optional[str], force: bool) -> None:
    """Generate entire project from a blueprint with dependencies (files generated alongside blueprints)."""
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Generating project from blueprint: {blueprint_file}")
        click.echo(f"Files will be generated alongside blueprint files")

    try:
        # Resolve blueprint dependencies
        resolver = BlueprintResolver(project_root=blueprint_file.parent.parent if blueprint_file.parent.name != "." else blueprint_file.parent)
        resolved = resolver.resolve(blueprint_file)
        
        if verbose:
            click.echo(f"  Main module: {resolved.main.module_name}")
            click.echo(f"  Total blueprints: {len(resolved.generation_order)}")
            click.echo(f"  Generation order:")
            for i, bp in enumerate(resolved.generation_order, 1):
                click.echo(f"    {i}. {bp.module_name}")
        
        # Generate code using Claude API with separate calls
        generator = CodeGenerator(api_key=api_key)
        generated_files = generator.generate_project(resolved, Path("."), language, force)
        
        click.echo(f"✓ Generated {len(generated_files)} files:")
        for module_name, file_path in generated_files.items():
            click.echo(f"  {module_name} -> {file_path}")
        
        if verbose:
            total_size = sum(f.stat().st_size for f in generated_files.values())
            click.echo(f"  Total size: {total_size} bytes")
            
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to generate project: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@main.command()
@click.argument("directory", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def discover(ctx: click.Context, directory: Path) -> None:
    """Discover blueprint files in a directory."""
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        click.echo(f"Discovering blueprints in: {directory}")

    # Find all .md files that look like blueprints
    blueprint_files = []
    for md_file in directory.rglob("*.md"):
        if md_file.name not in ["README.md", "CLAUDE.md", "BLUEPRINTS_SPEC.md"]:
            blueprint_files.append(md_file)

    if blueprint_files:
        click.echo(f"Found {len(blueprint_files)} blueprint files:")
        for bp_file in blueprint_files:
            click.echo(f"  {bp_file.relative_to(directory)}")
    else:
        click.echo("No blueprint files found")


@main.command()
@click.argument("module_name")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: current directory)",
)
@click.pass_context
def init(ctx: click.Context, module_name: str, output: Optional[Path]) -> None:
    """Initialize a new blueprint file."""
    verbose = ctx.obj.get("verbose", False)

    output_dir = output or Path.cwd()
    blueprint_file = output_dir / f"{module_name}.md"

    if verbose:
        click.echo(f"Creating blueprint file: {blueprint_file}")

    # Generate compact blueprint template
    template = f"""# {module_name}
Brief description of what this module does

deps: package1[dependency1]; package2[dependency2]

ExampleClass:
  - __init__(param: str)
  - method_name(param: str) -> str  # Description
  - property_name: str

example_function(param: int) -> bool:
  \"\"\"Function description\"\"\"
  # Implementation notes

CONSTANT_NAME: str = "value"

notes: implementation detail 1, performance consideration, future enhancement
"""

    blueprint_file.write_text(template)
    click.echo(f"✓ Created blueprint file: {blueprint_file}")


if __name__ == "__main__":
    main()
