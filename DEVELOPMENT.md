# Development Notes

This project is a simple email gateway with async IMAP/SMTP clients, sync
wrappers, connection pooling, and a FastMCP server.

## Project Structure

- `src/simple_email_gw/imap/client.py` - Async `IMAPClient`
- `src/simple_email_gw/imap/sync_client.py` - Sync `SyncIMAPClient` wrapper
- `src/simple_email_gw/smtp/client.py` - Async `SMTPClient`
- `src/simple_email_gw/smtp/sync_client.py` - Sync `SyncSMTPClient` wrapper
- `src/simple_email_gw/safety/` - Sanitization and audit logging helpers
- `src/simple_email_gw/mcp.py` - FastMCP tool definitions
- `src/simple_email_gw/connections/pool.py` - Connection pool and rate limits

## Recent Changes (P1-001)

- Added `append_email` MCP tool for pure IMAP `APPEND` of base64 RFC822 messages.
- Added `IMAPClient.append_message()` with folder validation, flag allowlist,
  NUL/size checks, timezone-aware `internal_date`, and generic error mapping.
- Added `IMAPClient.find_sent_folder()` using the IMAP `\Sent` special-use flag
  with fallback to common local names.
- Added `SMTPClient.send_email()` / `reply_email()` auto-append support with
  `append_to_sent`, `append_folder`, and injected `IMAPClient`.
- Added `SyncIMAPClient` and `SyncSMTPClient` wrappers for the new methods.
- Added `validate_append_flags()` in `safety/sanitize.py`.
- Added `log_email_appended()` in `safety/audit.py`.
- Added `get_append_max_size()` configurable via `EMAIL_APPEND_MAX_SIZE`
  (default 25 MB).
- Fixed `SMTPClient._auto_append()` to log successful auto-appends with
  `auto_append=True` (was only logging failure paths).

## Development Commands

```bash
make env-dev    # Install all dependencies
make test       # Run tests
make lint       # Run linter
make typecheck  # Run type checker
make format     # Format and auto-fix code
make check      # Run all checks
```

The project uses `uv` for dependency management. Always run commands via
`make` or `uv run` so the correct virtual environment is used.
