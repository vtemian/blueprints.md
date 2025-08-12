"""Main CLI entry point for blueprints.md."""

import click
from pathlib import Path
from typing import Optional

from blueprints import __version__
from blueprints.factory import create_quality_enhanced_generator
from blueprints.resolver import create_smart_resolver
from blueprints.logging_config import setup_logging, get_logger


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
    
    # Set up logging
    setup_logging(verbose)


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
@click.option("--quality-improvement/--no-quality-improvement", default=True,
              help="Enable iterative quality improvement (default: enabled)")
@click.option("--quality-iterations", type=int, default=2,
              help="Maximum quality improvement iterations (default: 2)")
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
    quality_improvement: bool,
    quality_iterations: int,
    verbose: bool
) -> None:
    """Generate source code from a blueprint file."""
    verbose = verbose or ctx.obj.get("verbose", False)
    logger = get_logger('cli')
    
    try:
        logger.info(f"Starting code generation for: {blueprint_file}")
        
        # Resolve dependencies
        logger.debug(f"Resolving dependencies from project root: {blueprint_file.parent}")
        project_root = blueprint_file.parent
        resolver = create_smart_resolver(project_root=project_root)
        resolved = resolver.resolve(blueprint_file)
        
        logger.info(f"Module: {resolved.main.module_name}")
        if resolved.dependencies:
            logger.info(f"Found {len(resolved.dependencies)} dependencies")
            for dep in resolved.dependencies:
                logger.debug(f"  - {dep.module_name}")
        else:
            logger.debug("No dependencies found")
        
        # Determine output path
        if not output:
            stem = blueprint_file.stem
            ext = get_file_extension(language)
            output = blueprint_file.parent / f"{stem}{ext}"
        
        logger.debug(f"Output path: {output}")
        logger.debug(f"Target language: {language}")
        logger.debug(f"Quality improvement: {quality_improvement}")
        if quality_improvement:
            logger.debug(f"Max quality iterations: {quality_iterations}")
        
        # Generate code
        logger.info("Creating code generator...")
        generator = create_quality_enhanced_generator(
            api_key=api_key, 
            enable_quality_improvement=quality_improvement,
            max_quality_iterations=quality_iterations
        )
        
        logger.info("Generating code...")
        output_path = generator.generate_single_with_context(
            resolved, output, language, force, True
        )
        
        click.echo(f"✅ Generated: {output_path}")
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise click.ClickException(f"Generation failed: {e}")


@main.command() 
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--language", "-l", default="python",
              help="Target language (default: python)")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY",
              help="Anthropic API key")
@click.option("--force", "-f", is_flag=True,
              help="Overwrite existing files")
@click.option("--quality-improvement/--no-quality-improvement", default=True,
              help="Enable iterative quality improvement (default: enabled)")
@click.option("--quality-iterations", type=int, default=2,
              help="Maximum quality improvement iterations (default: 2)")
@click.option("--verbose", "-v", is_flag=True,
              help="Verbose output")
@click.pass_context
def generate_project(
    ctx: click.Context,
    path: Path,
    language: str, 
    api_key: Optional[str],
    force: bool,
    quality_improvement: bool,
    quality_iterations: int,
    verbose: bool
) -> None:
    """Generate entire project from main blueprint."""
    verbose = verbose or ctx.obj.get("verbose", False)
    logger = get_logger('cli')
    
    try:
        logger.info(f"Starting project generation for: {path}")
        
        # Find main blueprint
        logger.debug(f"Looking for main blueprint in: {path}")
        blueprint_file = find_project_blueprint(path)
        logger.info(f"Using blueprint: {blueprint_file}")
        
        # Resolve dependencies
        logger.debug(f"Resolving dependencies from project root: {blueprint_file.parent}")
        project_root = blueprint_file.parent
        resolver = create_smart_resolver(project_root=project_root) 
        resolved = resolver.resolve(blueprint_file)
        
        logger.info(f"Total blueprints to generate: {len(resolved.generation_order)}")
        for i, blueprint in enumerate(resolved.generation_order, 1):
            logger.debug(f"  {i}. {blueprint.module_name}")
        
        logger.debug(f"Target language: {language}")
        logger.debug(f"Quality improvement: {quality_improvement}")
        if quality_improvement:
            logger.debug(f"Max quality iterations: {quality_iterations}")
        
        # Generate project
        logger.info("Creating code generator...")
        generator = create_quality_enhanced_generator(
            api_key=api_key, 
            enable_quality_improvement=quality_improvement,
            max_quality_iterations=quality_iterations
        )
        
        logger.info("Generating project files...")
        generated_files = generator.generate_project(
            resolved, Path("."), language, force, None, True
        )
        
        click.echo(f"✅ Generated {len(generated_files)} files:")
        for module_name, file_path in generated_files.items():
            click.echo(f"  📄 {module_name} -> {file_path}")
            
    except Exception as e:
        logger.error(f"Project generation failed: {e}")
        raise click.ClickException(f"Project generation failed: {e}")


if __name__ == "__main__":
    main()
