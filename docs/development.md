# Development Guide

This document provides information for developers contributing to simple-email-gw.

> **Note:** This package provides **both async and sync APIs**. Async clients (IMAPClient, SMTPClient) are the primary implementation. Sync wrapper clients (SyncIMAPClient, SyncSMTPClient) delegate to async clients using dedicated event loops.

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager

## Getting Started

### Clone and Install

```bash
git clone https://github.com/christophevg/simple-email-gw.git
cd simple-email-gw

# Install development dependencies
make dev-env
```

### Run Tests

```bash
make test
```

### Run Linter

```bash
make lint
```

### Type Check

```bash
make typecheck
```

### Run All Checks

```bash
make all
```

## Project Structure

```
simple-email-gw/
├── docs/                    # Documentation
│   ├── api.md               # API reference
│   ├── configuration.md     # Configuration options
│   ├── development.md       # Development guide
│   ├── installation.md      # Installation guide
│   ├── mcp-tools.md         # MCP tools reference
│   └── security.md          # Security features
├── src/simple_email_gw/     # Source code
│   ├── __init__.py
│   ├── config.py            # Configuration handling
│   ├── mcp.py               # MCP server
│   ├── imap/                # IMAP client
│   │   └── client.py
│   ├── smtp/                # SMTP client
│   │   └── client.py
│   ├── connections/         # Connection pooling
│   │   └── pool.py
│   └── safety/              # Security features
│       ├── audit.py
│       ├── rate_limiter.py
│       └── sanitize.py
├── tests/                   # Test suite
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_rate_limiter.py
│   ├── test_sanitize.py
│   └── test_whitelist.py
├── pyproject.toml
├── Makefile
└── README.md
```

## Code Style

### Formatting

- Use **two spaces** for indentation
- Maximum line length: 100 characters
- Use `ruff format` to auto-format

```bash
make format
```

### Linting

We use `ruff` for linting. Run it with:

```bash
make lint
```

### Type Annotations

All public functions should have type annotations. We use `mypy` for type checking:

```bash
make typecheck
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
uv run pytest tests/test_sanitize.py

# Run specific test
uv run pytest tests/test_sanitize.py::test_sanitize_subject
```

### Writing Tests

We use `pytest` with the following patterns:

```python
import pytest
from simple_email_gw import sanitize_subject


class TestSanitizeSubject:
  """Tests for subject line sanitization."""

  def test_removes_crlf(self):
    """CRLF sequences should be replaced with spaces."""
    result = sanitize_subject("Hello\r\nWorld")
    assert result == "Hello World"

  def test_removes_cr_only(self):
    """CR characters should be replaced with spaces."""
    result = sanitize_subject("Hello\rWorld")
    assert result == "Hello World"

  def test_handles_normal_text(self):
    """Normal text should pass through unchanged."""
    result = sanitize_subject("Normal subject")
    assert result == "Normal subject"
```

### Test Conventions

- Use descriptive test names
- Group related tests in classes
- Use `autouse=True` fixtures for setup
- Test both success and error paths

## MCP Server Development

### Running the Server

```bash
# Create .env file with credentials
cat > .env << EOF
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EOF

# Run the MCP server
make email-gw-mcp-server
```

### Adding New Tools

Add new MCP tools in `src/simple_email_gw/mcp.py`:

```python
@mcp.tool
async def new_tool(
  account: Annotated[str, Field(description="Account name")],
  ctx: Context = None,
) -> dict[str, str]:
  """Description of the new tool.

  Args:
    account: The account name.

  Returns:
    Dictionary with result.
  """
  if ctx:
    await ctx.info("Performing operation")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    # Do something
    return {"status": "ok"}
  except ValueError:
    raise ToolError(f"Account not found: {account}")
  except Exception:
    raise ToolError("Operation failed. Check server logs for details.")
```

## Building and Publishing

### Build Distribution

```bash
make build
```

This creates:
- `dist/simple_email_gw-0.1.0-py3-none-any.whl`
- `dist/simple_email_gw-0.1.0.tar.gz`

### Publish to PyPI

```bash
make publish
```

Requires PyPI credentials to be configured.

## Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### IMAP Debug Mode

```python
# Enable IMAP protocol logging
import aioimaplib
aioimaplib.log.setLevel(logging.DEBUG)
```

## Common Issues

### Import Errors

If you see import errors after adding new modules:

```bash
# Reinstall the package
make dev-env
```

### Test Failures

If tests fail after changes:

```bash
# Clean and reinstall
make clean
make dev-env
make test
```

### Type Checking Errors

If mypy reports errors:

1. Ensure all imports are properly typed
2. Check that return types match annotations
3. Run `uv run mypy src/ --show-error-codes` for details

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run all checks: `make all`
5. Commit with conventional format: `git commit -m "feat: add new feature"`
6. Push and create a pull request

### Commit Message Format

We use conventional commits:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## Release Process

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG (if exists)
3. Run `make all` to verify
4. Build and publish: `make build publish`
5. Create git tag: `git tag v0.x.x`
6. Push tag: `git push origin v0.x.x`