# Installation

## Requirements

- Python 3.10 or higher
- An email account (IMAP/SMTP access)
- **Async runtime** - All APIs are async and require `asyncio`

## Async-Only API

This package provides **async-only** APIs. All client methods must be called in async contexts:

```python
import asyncio
from simple_email_gw import IMAPClient

async def main():
    async with IMAPClient(account) as client:
        messages = await client.search(folder="INBOX")

asyncio.run(main())
```

## Install from PyPI

```bash
pip install simple-email-gw
```

## Install with uv

```bash
uv add simple-email-gw
```

## Run with uvx (one-off execution)

For running the MCP server without installation:

```bash
uvx --from simple-email-gw mcp-server
```

## Development Installation

Clone the repository and install development dependencies:

```bash
git clone https://github.com/christophevg/simple-email-gw.git
cd simple-email-gw
make dev-env
```

Run tests:

```bash
make test
```

Run all checks:

```bash
make all
```

## Dependencies

### Required Dependencies

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP server framework |
| `aioimaplib` | Async IMAP client |
| `aiosmtplib` | Async SMTP client |
| `pydantic` | Data validation |
| `pydantic-settings` | Settings management |

### Optional Dependencies

| Package | Purpose |
|---------|---------|
| `python-dotenv` | Load environment from .env files |

## Verifying Installation

Check that the package is installed correctly:

```bash
python -c "from simple_email_gw import IMAPClient; print('OK')"
```

## Next Steps

- [Configuration](configuration.md) - Configure email accounts
- [Security](security.md) - Security features overview
- [API Reference](api.md) - Complete API documentation