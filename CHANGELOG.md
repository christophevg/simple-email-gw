# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- Corrected recipient whitelist env var names in README and docs (`EMAIL_RECIPIENT_WHITELIST_DOMAINS` / `EMAIL_RECIPIENT_WHITELIST_ADDRESSES`). The previously documented `EMAIL_RECIPIENT_DOMAINS` / `EMAIL_RECIPIENT_ADDRESSES` were never read by the code, silently leaving the whitelist disabled (fail-open).
- Corrected rate-limit env var names in `.env.example` and `docs/cli.md` to match the code (`EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE` / `EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR`). The previously documented `EMAIL_RATE_LIMIT_REQUESTS_PER_MINUTE` / `EMAIL_RATE_LIMIT_SENDS_PER_HOUR` were never read by the code.
- Added fail-open warning to recipient whitelist documentation in `docs/security.md` and `docs/configuration.md`.

## 0.3.0 - 2026-06-17

### Added

- IMAP append tool with `auto_append` and `append_folder` support for saving sent/replied messages.
- CLI `write`/`reply` commands now support `--sent` and `--sent-folder` options.
- MCP `send_email` and `reply_email` tools validate `append_folder` overrides.
- Audit logging for successful auto-appended messages.

### Changed

- Refactored SMTP client return types and extracted sent-folder flags constant.
- Refactored IMAP client to reuse append error mapping and audit-log failures consistently.

### Fixed

- Aligned package `__version__` with `pyproject.toml`.
- Disabled Sent-folder append when the IMAP client is unavailable.
- Reset `append_folder` state when the IMAP client is unavailable.
- Applied RFC 3501 mailbox quoting across all `aioimaplib` calls.
- IMAP-quoted mailbox names in `APPEND` to avoid server parse errors.
- Patched `prompt_toolkit` output in tests for Windows CI compatibility.
