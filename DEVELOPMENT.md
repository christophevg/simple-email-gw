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

## Post-Review Fixes (P1-001)

- Fixed `_compose_and_send()` to disable `append_to_sent` when the session
  IMAP client cannot be obtained, so the email still sends without attempting
  the Sent-folder append. A warning is still shown to the user. Added CLI
  tests covering `write --sent` and `reply --sent` with an unavailable IMAP
  client.

## Review Feedback Fixes (P1-001)

- Aligned `__version__` in `src/simple_email_gw/__init__.py` with `pyproject.toml`
  (`0.2.1`).
- Refactored `IMAPClient.append_message()` to use the `_APPEND_ERROR_MESSAGES`
  mapping instead of duplicated inline error strings.
- Added failure audit logging (`log_email_appended(..., success=False, ...)`)
  in all `IMAPClient.append_message()` error branches before re-raising.
- Validated `append_folder` at the MCP layer in `send_email` and `reply_email`
  tools before forwarding to the SMTP client.
- Tightened return type annotations for `SMTPClient.send_email()` and
  `reply_email()` (and their sync wrappers) to `dict[str, str | bool | None]`.
- Extracted module-level constants: `SENT_FOLDER_FALLBACKS` in `imap/client.py`
  and `APPEND_SENT_FLAGS` in `smtp/client.py`.
- Added tests for: timezone-aware `internal_date`, `flags=None`, direct
  append failure audit logging, first `\Sent` selection, auto-append size-cap
  warning, CRLF injection in address headers for `append_email`,
  `get_append_max_size()` default/invalid fallback, and audit-log truncation
  boundaries.

- Added CLI support for auto-append-to-Sent on `write` and `reply` commands:
  - `--sent` / `--save-sent` opt-in flag (default `False`).
  - `--sent-folder FOLDER` override (must be paired with `--sent`).
  - Interactive `Save a copy to Sent folder? (y/n)` prompt during the compose flow.
  - `reply` now uses `SMTPClient.reply_email()` and passes the session IMAP
    client and `append_folder` to the SMTP client.
  - `EmailDraft` carries `append_to_sent` and `append_folder`; the preview table
    shows the Sent save choice.

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
