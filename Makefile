-include ~/.claude/Makefile

# Makefile for simple-email-gw
# Utility targets for common development actions

.PHONY: run-env dev-env test test-all lint format typecheck build publish clean all help docs

## run-env: Install production dependencies
run-env:
	uv sync

## dev-env: Install with all dependencies (dev, docs, extras)
dev-env:
	uv sync --all-extras

## test: Run tests with pytest
test: dev-env
	uv run pytest

## test-all: Run tests with tox (all Python versions)
test-all: dev-env
	uv run tox

## test-cov: Run tests with coverage report
test-cov: dev-env
	uv run pytest --cov=src/simple_email_gw --cov-report=term-missing

## lint: Run ruff linting
lint: dev-env
	uv run ruff check src/ tests/

## format: Format code with ruff
format: dev-env
	uv run ruff format src/ tests/

## typecheck: Run mypy type checking
typecheck: dev-env
	uv run mypy src/

## docs: Build documentation
docs: dev-env
	cd docs && uv run sphinx-build -b html . _build/html

## build: Build distribution packages
build: dev-env
	uv build

## publish: Publish to PyPI (requires credentials)
publish: build
	uv run twine upload dist/*

## publish-test: Publish to TestPyPI (requires credentials)
publish-test: build
	uv run twine upload --repository testpypi dist/*

## clean: Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .coverage .mypy_cache
	rm -rf docs/_build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

## check: Run lint, test, and typecheck
check: dev-env
	uv run ruff check src/ tests/
	uv run pytest
	uv run mypy src/

## email-gw-mcp-server: Run the MCP server
email-gw-mcp-server: run-env
	uv tool run --with . email-gw-mcp-server

## help: Show this help message
help:
	@echo "Available targets:"
	@echo ""
	@sed -n 's/^## //p' $(MAKEFILE_LIST) | column -t -s ':'
