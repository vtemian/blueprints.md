# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

blueprints.md is a markdown-to-code generation system where developers write `.md` blueprint files and coding agents generate the actual source code.

## Key Concepts

- **Blueprint files (.md)** are co-located with source files (like .js and .js.map)
- **Coding agents** read `.md` files instead of actual source files to understand the system
- **Blueprint files** are the source of truth - read and modify these instead of source files
- **Generated code** should match the specifications in the corresponding `.md` file
- When making changes, update the `.md` file first, then regenerate code

## Development Commands

```bash
# Development environment
uv sync

# Code formatting
uv run black .

# Testing
uv run pytest
uv run pytest --cov

# Type checking
uv run mypy .

# CLI tool
uv run blueprints --help

# Code verification (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=your_key_here
uv run blueprints generate-project examples/task_api/
```

## Blueprint Format

Natural language format (see BLUEPRINTS_SPEC.md for full details):
- `# module.name` - Module declaration on first line
- Natural description of what the module should do
- `Dependencies:` - External libraries and blueprint references
- `Requirements:` - Key functional and technical requirements  
- Additional sections as needed (Business Context, Security Notes, etc.)

## Important Notes

- Blueprint files are the source of truth for system architecture
- **Pure Claude System**: Requires `ANTHROPIC_API_KEY` environment variable for all operations
- **Intelligent parsing**: Claude understands natural language blueprints using BLUEPRINTS_SPEC.md as context
- **Intelligent verification**: Claude analyzes generated code against blueprint requirements
- **No regex parsing**: System uses AI for all blueprint understanding - more flexible and powerful