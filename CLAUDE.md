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

# CLI tool (when implemented)
uv run blueprints --help
```

## Blueprint Format

Compact format:
- `# module.name` - Module declaration on first line
- `deps:` - Dependencies in compact format
- Component definitions (classes, functions, constants)
- `notes:` - Implementation notes

## Important Notes

- Blueprint files are the source of truth for system architecture
- The CLI implementation is missing and needs to be created in `src/blueprints/cli/`