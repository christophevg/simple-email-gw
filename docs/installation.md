# Installation

## Requirements

- Python 3.10 or higher
- An email account (IMAP/SMTP access)

## Choosing Async or Sync

This package provides **both async and sync APIs**:

- **Async clients** (IMAPClient, SMTPClient): For async applications (FastAPI, Quart, asyncio)
- **Sync clients** (SyncIMAPClient, SyncSMTPClient): For simpler synchronous code (scripts, CLI tools)

### Async Usage

```python
import asyncio
from simple_email_gw import IMAPClient, EmailAccount

async def main():
    account = EmailAccount(name="work", imap_host="imap.gmail.com", ...)
    async with IMAPClient(account) as client:
        messages = await client.search(folder="INBOX")

asyncio.run(main())
```

### Sync Usage

```python
from simple_email_gw import SyncIMAPClient, EmailAccount

account = EmailAccount(name="work", imap_host="imap.gmail.com", ...)
with SyncIMAPClient(account) as client:
    messages = client.search(folder="INBOX")
```

See [Sync Client API Reference](sync-clients) for complete sync client documentation.

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
uvx --from simple-email-gw email-gw-mcp-server
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