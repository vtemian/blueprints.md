"""Main CLI entry point for blueprints.md."""

import click
from pathlib import Path
from typing import Optional

from blueprints import __version__
from blueprints.generator import CodeGenerator
from blueprints.resolver import BlueprintResolver


def get_file_extension(language: str) -> str:
    """Get file extension for language."""
    extensions = {
        "python": ".py",
        "javascript": ".js", 
        "typescript": ".ts",
        "java": ".java",
        "go": ".go",
        "rust": ".rs"
    }
    return extensions.get(language.lower(), ".txt")


def find_project_blueprint(path: Path) -> Path:
    """Find main blueprint file in project directory."""
    if not path.is_dir():
        return path
        
    for candidate in ["main.md", "app.md"]:
        blueprint_file = path / candidate
        if blueprint_file.exists():
            return blueprint_file
            
    raise click.ClickException(f"No main blueprint found in {path}")


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
@click.option("--output", "-o", type=click.Path(path_type=Path), 
              help="Output file path")
@click.option("--language", "-l", default="python", 
              help="Target language (default: python)")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY", 
              help="Anthropic API key")
@click.option("--force", "-f", is_flag=True, 
              help="Overwrite existing files")
@click.option("--verbose", "-v", is_flag=True, 
              help="Verbose output")
@click.pass_context
def generate(
    ctx: click.Context,
    blueprint_file: Path, 
    output: Optional[Path],
    language: str,
    api_key: Optional[str],
    force: bool,
    verbose: bool
) -> None:
    """Generate source code from a blueprint file."""
    verbose = verbose or ctx.obj.get("verbose", False)
    
    try:
        # Resolve dependencies
        project_root = blueprint_file.parent
        resolver = BlueprintResolver(project_root=project_root)
        resolved = resolver.resolve(blueprint_file)
        
        if verbose:
            click.echo(f"Module: {resolved.main.module_name}")
            if resolved.dependencies:
                click.echo(f"Dependencies: {len(resolved.dependencies)}")
        
        # Determine output path
        if not output:
            stem = blueprint_file.stem
            ext = get_file_extension(language)
            output = blueprint_file.parent / f"{stem}{ext}"
        
        # Generate code
        generator = CodeGenerator(api_key=api_key)
        output_path = generator.generate_single_with_context(
            resolved, output, language, force, True
        )
        
        click.echo(f"Generated: {output_path}")
        
    except Exception as e:
        raise click.ClickException(f"Generation failed: {e}")


@main.command() 
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--language", "-l", default="python",
              help="Target language (default: python)")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY",
              help="Anthropic API key")
@click.option("--force", "-f", is_flag=True,
              help="Overwrite existing files")
@click.option("--verbose", "-v", is_flag=True,
              help="Verbose output")
@click.pass_context
def generate_project(
    ctx: click.Context,
    path: Path,
    language: str, 
    api_key: Optional[str],
    force: bool,
    verbose: bool
) -> None:
    """Generate entire project from main blueprint."""
    verbose = verbose or ctx.obj.get("verbose", False)
    
    try:
        # Find main blueprint
        blueprint_file = find_project_blueprint(path)
        
        if verbose:
            click.echo(f"Using blueprint: {blueprint_file}")
        
        # Resolve dependencies
        project_root = blueprint_file.parent
        resolver = BlueprintResolver(project_root=project_root) 
        resolved = resolver.resolve(blueprint_file)
        
        if verbose:
            click.echo(f"Total blueprints: {len(resolved.generation_order)}")
        
        # Generate project
        generator = CodeGenerator(api_key=api_key)
        generated_files = generator.generate_project(
            resolved, Path("."), language, force, None, True
        )
        
        click.echo(f"Generated {len(generated_files)} files:")
        for module_name, file_path in generated_files.items():
            click.echo(f"  {module_name} -> {file_path}")
            
    except Exception as e:
        raise click.ClickException(f"Project generation failed: {e}")


if __name__ == "__main__":
    main()
