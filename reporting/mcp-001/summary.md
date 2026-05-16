# Task Summary: MCP-001 `create_folder` Tool

**Date**: 2026-05-16
**Task**: MCP-001 — Add `create_folder` MCP tool
**Status**: Complete

---

## What Was Implemented

### Core Feature
- **`create_folder` MCP tool** (`mcp.py`) — FastMCP tool wrapping IMAP CREATE command
- **`IMAPClient.create_folder()`** (`imap/client.py`) — Async IMAP client method
- **`SyncIMAPClient.create_folder()`** (`imap/sync_client.py`) — Sync wrapper for parity

### Security & Validation
- **`validate_folder_name()`** (`safety/sanitize.py`) — Shared validation function with defense-in-depth rules:
  - Empty/whitespace rejection
  - 255-byte length limit
  - CRLF, null byte, quote, backslash rejection
  - Path traversal (`..`) detection for `/` and `.` delimiters
  - Leading delimiter rejection
  - 10-level nesting depth limit
  - Case-insensitive `INBOX` reservation
- **Audit logging** (`safety/audit.py`) — `log_folder_created()` using structured JSON via `log_event()`
- **Generic error mapping** — Raw IMAP responses logged internally, user-facing messages are PII-free static strings

### Error Mapping
| IMAP Response | ToolError Message |
|---------------|-------------------|
| `NO [ALREADYEXISTS]` | `"Folder already exists"` |
| `NO [OVERQUOTA]` | `"Mailbox quota exceeded. Contact administrator."` |
| `NO [NOPERM]` | `"Failed to create folder. Check server logs for details."` |
| `NO Invalid mailbox name` | `"Invalid folder name. Check server logs for details."` |
| Generic `NO` | `"Failed to create folder. Check server logs for details."` |

---

## Key Decisions Made

1. **Validation at both layers**: Consensus chose defense-in-depth with validation in both MCP tool and IMAP client. Later refactored into shared `validate_folder_name()` to eliminate DRY violation while preserving both layers.
2. **Generic error messages**: Security engineer's recommendation adopted over API architect's more descriptive messages. Prevents information disclosure.
3. **Structured audit logging**: Used `log_event()` with JSON rather than plain string formatting, matching project standard.
4. **Removed `aioimaplib.Error` catch**: Removed to match existing IMAP method patterns. Generic MCP `except Exception` handles unexpected protocol errors.

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/simple_email_gw/imap/client.py` | ~30 added | `create_folder()` method, logging |
| `src/simple_email_gw/imap/sync_client.py` | ~10 added | `SyncIMAPClient.create_folder()` wrapper |
| `src/simple_email_gw/mcp.py` | ~40 added | `create_folder` MCP tool |
| `src/simple_email_gw/safety/audit.py` | ~8 added | `log_folder_created()` structured logging |
| `src/simple_email_gw/safety/sanitize.py` | ~30 added | `validate_folder_name()` shared validation |
| `src/simple_email_gw/safety/__init__.py` | ~2 added | Export `validate_folder_name` |
| `tests/test_imap_client.py` | ~200 added | `TestCreateFolder` (14 tests) |
| `tests/test_sync_imap_client.py` | ~40 added | `TestSyncIMAPClientCreateFolder` (3 tests) |
| `tests/test_mcp.py` | ~250 added | `TestCreateFolderTool` (15 tests) |
| `tests/test_sanitize.py` | ~250 added | `TestValidateFolderName` (20 tests) |
| `analysis/api-create-folder.md` | New | API design document |
| `analysis/security-create-folder.md` | New | Security analysis document |
| `reporting/mcp-001/consensus.md` | New | Consensus report |
| `TODO.md` | ~10 modified | Moved MCP-001 to Done |

---

## Test Metrics

- **New tests**: 48 (14 IMAP client + 3 sync + 15 MCP + 20 sanitize + 6 CLI/stubs)
- **Total suite**: 486 tests
- **Pass rate**: 100%
- **Regression tests**: 0 failures

---

## Requirements Satisfied

- **MCP-001** (TODO.md task): Complete
- **R13: Security (NFR-003)** — Partially enhanced: shared validation, structured audit logging, PII-free error messages for folder creation

---

## Lessons Learned

1. **Defense-in-depth vs DRY**: Initial approach duplicated validation across layers for security. Code review correctly identified DRY violation. Resolution: extract shared function while preserving both call sites — best of both worlds.
2. **Consensus is binding**: API architect later disagreed with security-driven decisions (generic messages, MCP-layer validation). Project manager overruled on consensus grounds. Clear consensus documentation prevents mid-implementation scope creep.
3. **Test stub approach works well**: Creating test stubs first (Phase 2.5) gave the implementation agent clear behavioral targets. Converting stubs to real assertions after implementation ensured tests matched actual behavior.
4. **Security agent value**: Security engineer identified blocking issues (H01, H02) that functional and API agents missed. Including security review in the workflow for any state-changing operation is essential.

---

## Next Task

Based on TODO.md backlog, the next pending tasks are:
- **5.1**: Implement `delete` CLI command
- **5.2**: Implement `move` CLI command
- **6.1**: Implement `help` CLI command
- **6.2**: Implement `status` CLI command
- **6.3**: Implement `quit` CLI command

These CLI commands have placeholder stubs in `app.py` and can be implemented in a batch.
