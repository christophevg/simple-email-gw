# simple-email-gw

[![PyPI](https://img.shields.io/pypi/v/simple-email-gw.svg)][pypi]
[![Python](https://img.shields.io/pypi/pyversions/simple-email-gw.svg)][pypi]
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)][uv]
[![CI](https://img.shields.io/github/actions/workflow/status/christophevg/simple-email-gw/ci.yml.svg)][ci]
[![Coverage](https://img.shields.io/coveralls/github/christophevg/simple-email-gw.svg)][coveralls]
[![License](https://img.shields.io/github/license/christophevg/simple-email-gw.svg)][license]
[![Agentic](https://img.shields.io/badge/workflow-agentic-blueviolet?style=flat-square)](https://christophe.vg/about/Agentic-Workflow)

A simple email gateway with IMAP/SMTP clients, connection pooling, and MCP server for AI assistant integration.

> **Note:** This package provides both async and sync APIs. Async clients are recommended for async applications. Use sync wrapper clients (SyncIMAPClient, SyncSMTPClient) for simpler synchronous code.

## Rationale

This project was built using an agentic workflow — agents created the implementation from architectural requirements. For the full story, see the `rationale documentation <https://simple-email-gw.readthedocs.io/en/latest/rationale.html>`_.

## Features

- Async IMAP and SMTP clients (aioimaplib, aiosmtplib)
- **Sync wrapper clients** for simpler synchronous usage (SyncIMAPClient, SyncSMTPClient)
- Connection pooling with automatic management
- Token bucket rate limiting
- Audit logging for security compliance
- CRLF injection prevention
- Recipient whitelist enforcement
- TLS 1.2+ minimum encryption
- MCP server for AI assistant integration

## Installation

### Using pip

```bash
pip install simple-email-gw
```

### Using uv

```bash
uv add simple-email-gw
```

## Quick Start

### MCP Server

Run the MCP server for AI assistant integration:

```bash
# Set environment variables
export EMAIL_IMAP_HOST=imap.gmail.com
export EMAIL_SMTP_HOST=smtp.gmail.com
export EMAIL_USERNAME=your-email@gmail.com
export EMAIL_PASSWORD=your-app-password

# Run server
uvx --from simple-email-gw email-gw-mcp-server
```

### Programmatic Usage

```python
import asyncio
from simple_email_gw import IMAPClient, SMTPClient, EmailAccount

# Create account configuration
account = EmailAccount(
  name="work",
  imap_host="imap.gmail.com",
  smtp_host="smtp.gmail.com",
  username="user@gmail.com",
  password="app-password"
)

async def main():
  # Use IMAP client
  async with IMAPClient(account) as client:
    folders = await client.list_folders()
    messages = await client.search(folder="INBOX")
    print(f"Found {len(messages)} messages")

  # Use SMTP client
  smtp = SMTPClient(account)
  result = await smtp.send_email(
    to=["recipient@example.com"],
    subject="Test",
    body="Hello world"
  )
  print(f"Sent: {result}")

asyncio.run(main())
```

### Sync Client Usage

For simpler synchronous code, use the sync wrapper clients:

```python
from simple_email_gw import SyncIMAPClient, SyncSMTPClient, EmailAccount

# Create account configuration
account = EmailAccount(
  name="work",
  imap_host="imap.gmail.com",
  smtp_host="smtp.gmail.com",
  username="user@gmail.com",
  password="app-password"
)

# Sync IMAP usage
with SyncIMAPClient(account) as client:
  folders = client.list_folders()
  messages = client.search(folder="INBOX")
  print(f"Found {len(messages)} messages")

# Sync SMTP usage
with SyncSMTPClient(account) as client:
  result = client.send_email(
    to=["recipient@example.com"],
    subject="Test",
    body="Hello world"
  )
  print(f"Sent: {result}")
```

### Interactive CLI

Run the interactive CLI for managing email:

```bash
# Create .env file with your email account
cp .env.example .env
# Edit .env with your account details

# Run CLI
uv run email-gw-cli

# Or if installed globally
email-gw-cli
```

**Getting Started:**

```bash
none:INBOX> help                    # Show available commands
none:INBOX> accounts                # List configured accounts
none:INBOX> use work                # Connect to 'work' account
work:INBOX> folders                 # List folders
work:INBOX> ls                      # List emails
work:INBOX> show 42                 # View email #42
work:INBOX> write --sent alice@example.com   # Compose and save copy to Sent
work:INBOX> reply --sent 42         # Reply and save copy to Sent
work:INBOX> write --sent --sent-folder "Sent Items" alice@example.com  # Custom Sent folder
work:INBOX> theme                   # Toggle light/dark theme
work:INBOX> quit                    # Exit CLI
```

The `--sent` flag (also `--save-sent`) enables opt-in auto-append to the IMAP Sent folder after a successful send. It triggers a `Save a copy to Sent folder? (y/n)` prompt and can be combined with `--sent-folder` to override the destination folder.

**Features:**

- **Command history** - Use ↑/↓ arrows to navigate previous commands
- **Theme support** - Switch between light and dark color themes
- **Auto-completion** - Tab completion for commands (coming soon)
- **Rich formatting** - Tables, panels, and syntax-highlighted output

See the [CLI documentation](https://simple-email-gw.readthedocs.io/en/latest/cli.html) for complete command reference.

> **Note:** Sync clients use a dedicated event loop in a background thread (Strategy 2). They preserve all async client benefits including connection pooling, rate limiting, and security features. Use async clients in async contexts (FastAPI, asyncio, etc.) for better performance.

## Configuration

### Environment Variables

The CLI and MCP server automatically load environment variables from a `.env` file in the current directory. Copy `.env.example` to `.env` and configure your email accounts:

```bash
cp .env.example .env
# Edit .env with your email account details
```

Single account configuration:

```bash
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=user@gmail.com
EMAIL_PASSWORD=app-password
```

Multiple accounts (JSON):

```bash
EMAIL_ACCOUNTS_JSON='[{"name":"work","imap_host":"imap.gmail.com","smtp_host":"smtp.gmail.com","username":"work@example.com","password":"secret"},{"name":"personal","imap_host":"imap.icloud.com","smtp_host":"smtp.icloud.com","username":"personal@icloud.com","password":"secret"}]'
```

See the `configuration documentation <https://simple-email-gw.readthedocs.io/en/latest/configuration.html>`_ for detailed options.

### Rate Limiting

Default limits:
- IMAP: 60 requests per minute per account
- SMTP: 100 sends per hour per account

### Recipient Whitelist

Restrict outgoing emails to specific domains or addresses:

```bash
EMAIL_RECIPIENT_DOMAINS=gmail.com,icloud.com
EMAIL_RECIPIENT_ADDRESSES=admin@company.com
```

## Security Features

### TLS 1.2+ Minimum

All connections require TLS 1.2 or higher. Connections with older TLS versions are rejected.

### CRLF Injection Prevention

All email headers are sanitized to prevent CRLF injection attacks:
- Subject lines
- Message-IDs
- References headers
- Email addresses

### Recipient Whitelist

Optional whitelist restricts outgoing emails to approved recipients.

### Rate Limiting

Token bucket algorithm prevents abuse with separate limits per account.

### Audit Logging

All operations are logged for security compliance.

See the `security documentation <https://simple-email-gw.readthedocs.io/en/latest/security.html>`_ for complete details.

## MCP Tools

| Tool | Purpose |
|------|---------|
| `list_accounts` | List configured email accounts |
| `list_folders` | List IMAP folders |
| `search_emails` | Search messages by criteria |
| `get_email` | Fetch single message |
| `download_attachment` | Download attachment to workspace |
| `send_email` | Send new email (optional auto-save to Sent) |
| `reply_email` | Reply to thread (optional auto-save to Sent) |
| `move_email` | Move between folders |
| `delete_email` | Delete message |
| `mark_email_read` | Mark message as read |
| `append_email` | Append a raw RFC822 message to an IMAP folder |

### Auto-Save Sent Folder

`send_email` and `reply_email` support optional auto-append to the account's Sent folder:

- `append_to_sent: bool` - Append a copy after a successful SMTP send (default: `False`).
- `append_folder: str | None` - Override the destination folder (default: auto-detected Sent folder).

The Sent folder is detected using the IMAP `\Sent` special-use flag when available, with a deterministic fallback to `Sent`, `Sent Items`, and `Sent Messages`. If auto-append fails, the send still succeeds and a warning is returned.

### Append Email Tool

`append_email` performs a pure IMAP `APPEND` of a base64-encoded RFC822 message. The message is re-parsed, threading headers are sanitized, and flags are restricted to the allowlist `\Seen`, `\Draft`, `\Answered`, `\Flagged`.

See the `API documentation <https://simple-email-gw.readthedocs.io/en/latest/api.html>`_ for complete API reference.

## Development

See the `development documentation <https://simple-email-gw.readthedocs.io/en/latest/development.html>`_ for development setup and contribution guidelines.

Quick commands:

```bash
make dev-env    # Install development dependencies
make test       # Run tests
make lint       # Run linter
make typecheck  # Run type checker
make all        # Run all checks
make email-gw-mcp-server # Run the MCP server
```

## License

MIT License - see [LICENSE](LICENSE) for details.

[pypi]: https://pypi.org/project/simple-email-gw/
[uv]: https://docs.astral.sh/uv/
[ci]: https://github.com/christophevg/simple-email-gw/actions
[coveralls]: https://coveralls.io/github/christophevg/simple-email-gw
[license]: https://github.com/christophevg/simple-email-gw/blob/main/LICENSE
