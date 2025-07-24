.PHONY: help install dev test lint format clean run

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## Install the package
	uv sync

dev:  ## Install development dependencies
	uv sync --dev

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage
	uv run pytest --cov

lint:  ## Run linting checks
	uv run mypy src/
	uv run black --check src/ tests/

format:  ## Format code
	uv run black src/ tests/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run the CLI tool
	uv run blueprints

# Example commands
example-init:  ## Initialize an example blueprint
	uv run blueprints init example_service -o examples/

example-validate:  ## Validate example blueprint
	uv run blueprints validate examples/example_service.md

example-generate:  ## Generate code from example blueprint
	uv run blueprints generate examples/example_service.md

example-discover:  ## Discover blueprints in examples
	uv run blueprints discover examples/

# Development workflow
dev-setup: dev  ## Set up development environment
	@echo "Development environment ready!"

dev-test: format lint test  ## Run full development test suite

dev-watch:  ## Watch for changes and run tests (requires entr)
	find src/ tests/ -name "*.py" | entr -c make test