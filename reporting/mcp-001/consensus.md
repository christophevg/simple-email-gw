# Consensus Report: MCP-001 `create_folder` Tool

**Date**: 2026-05-16
**Task**: MCP-001 - Add `create_folder` MCP tool
**Status**: Approved for implementation

---

## 1. Consensus Summary

All domain agents agree on the overall architecture. The security engineer identified **two blocking findings** (H01: IMAP command injection, H02: Path traversal) that require additional input validation beyond what the API architect initially proposed. The consensus adopts the API architect's structural design with the security engineer's validation requirements layered on top.

---

## 2. Agreed Architecture

### 2.1 IMAPClient Method (`imap/client.py`)

```python
async def create_folder(self, folder_name: str) -> bool:
```

**Pattern**: Follow existing `select_folder`, `move_message` pattern exactly:
1. Acquire `self._operation_lock`
2. Call `await self.connect()`
3. Validate/sanitize folder name (see §3)
4. Invoke `await client.create(safe_folder)` via `aioimaplib`
5. Inspect response:
   - `status == "OK"`: return `True`
   - `status == "NO"`: raise `RuntimeError` with mapped message
6. Catch `aioimaplib.Error` and raise `RuntimeError` with generic message

**Returns**: `True` on success

**Raises**:
- `ValueError` — invalid folder name (validation failures)
- `RuntimeError` — IMAP server rejection (already exists, permission denied, etc.)

### 2.2 MCP Tool (`mcp.py`)

```python
@mcp.tool
async def create_folder(
    account: Annotated[str, Field(description="Account name")],
    folder_name: Annotated[str, Field(description="Name of the folder to create")],
    ctx: Context | None = None,
) -> dict[str, str]:
```

**Pattern**: Follow existing `list_folders`, `move_email`, `delete_email` pattern:
1. Log intent via `ctx.info()`
2. Validate `folder_name` at MCP layer (see §3.1)
3. Get pool and IMAP client
4. Delegate to `client.create_folder(folder_name)`
5. Call `log_folder_created(account, folder_name)` on success
6. Return `{"status": "created", "folder": folder_name}`

**Exception handling**:
- `ValueError` → `ToolError` with message
- `RateLimitError` → `ToolError("Rate limit exceeded...")`
- `RuntimeError` → `ToolError` with mapped message
- Generic `Exception` → `ToolError("Failed to create folder...")`

### 2.3 Sync Wrapper (`imap/sync_client.py`)

Add `create_folder()` sync wrapper to `SyncIMAPClient` for parity with all other public methods, delegating via `_run_coroutine()`.

---

## 3. Input Validation Requirements (Security-Driven)

### 3.1 MCP Tool Layer Validations

Applied **before** calling `IMAPClient.create_folder()`:

| Check | Rule | Error |
|-------|------|-------|
| Empty | `len(folder_name.strip()) == 0` | `ToolError("Folder name cannot be empty")` |
| Length | `len(folder_name.encode("utf-8")) > 255` | `ToolError("Folder name exceeds maximum length")` |
| CRLF | `"\r" in folder_name or "\n" in folder_name` | `ToolError("Folder name contains invalid characters")` |
| Null byte | `"\x00" in folder_name` | `ToolError("Folder name contains invalid characters")` |
| Quote/backslash | `"\"" in folder_name or "\\" in folder_name` | `ToolError("Folder name contains invalid characters")` |
| Traversal | `".." in folder_name.split("/")` or `".." in folder_name.split(".")` | `ToolError("Invalid folder name")` |
| Leading delimiter | `folder_name.startswith(("/", "."))` | `ToolError("Invalid folder name")` |
| Depth | `len(folder_name.split("/")) > 10` and `len(folder_name.split(".")) > 10` | `ToolError("Folder nesting exceeds maximum depth")` |
| Reserved name | `folder_name.strip().upper() == "INBOX"` | `ToolError("INBOX is a reserved folder name")` |
| Whitespace | `folder_name = folder_name.strip()` | Transform silently |

**Note**: Both `/` and `.` are treated as potential hierarchy delimiters for traversal/depth checks, since the server delimiter is not known at validation time.

### 3.2 IMAP Client Layer Validations

Defense-in-depth validations in `IMAPClient.create_folder()`:

1. Call `sanitize_folder_name(folder_name)` for CRLF prevention
2. Reject `"`, `\`, `\x00` — raise `ValueError`
3. Reject `..` in split by `/` or `.` — raise `ValueError`
4. Reject leading `/` or `.` — raise `ValueError`
5. Reject empty after strip — raise `ValueError`

### 3.3 Pydantic Field Constraints

```python
folder_name: Annotated[
    str,
    Field(description="Name of the folder to create", min_length=1, max_length=255),
]
```

---

## 4. Error Mapping

| IMAP Server Response | MCP ToolError Message |
|----------------------|-----------------------|
| `NO [ALREADYEXISTS]` | `"Folder already exists"` |
| `NO [NOPERM]` | `"Failed to create folder. Check server logs for details."` |
| `NO Invalid mailbox name` | `"Invalid folder name. Check server logs for details."` |
| `NO Quota exceeded` | `"Mailbox quota exceeded. Contact administrator."` |
| Protocol/connection errors | `"Failed to create folder. Check server logs for details."` |

**Rules**:
- Never echo raw server text to the client
- Never echo suspicious `folder_name` back in error messages
- Log full server responses internally at DEBUG/WARNING

---

## 5. Audit Logging

Add to `safety/audit.py`:

```python
def log_folder_created(account_name: str, folder_name: str) -> None:
    """Log a folder creation event."""
    logger.info("folder_created account=%s folder=%s", account_name, folder_name)
```

Call from `mcp.py` `create_folder` tool on success.

---

## 6. Rate Limiting

**Current**: Share existing `imap_limiter` (60 req/min).

**Recommended follow-up**: Add separate `imap_write_limiter` (10 req/min) for state-changing IMAP operations (CREATE, DELETE, MOVE). Out of scope for MCP-001 to avoid scope creep, but noted as a post-implementation enhancement.

---

## 7. Files to Modify

| File | Change |
|------|--------|
| `src/simple_email_gw/imap/client.py` | Add `create_folder()` async method |
| `src/simple_email_gw/imap/sync_client.py` | Add `create_folder()` sync wrapper |
| `src/simple_email_gw/mcp.py` | Add `create_folder` MCP tool |
| `src/simple_email_gw/safety/audit.py` | Add `log_folder_created()` |
| `tests/test_imap_client.py` | Add async client tests |
| `tests/test_sync_imap_client.py` | Add sync wrapper tests |
| `tests/test_mcp.py` | Add MCP tool tests (new or existing suite) |

---

## 8. Test Plan

### 8.1 Async IMAP Client Tests
- `test_create_folder_success` — mock `client.create` returning `OK`
- `test_create_folder_sanitization_rejects_crlf` — `ValueError` on `"Bad\r\nFolder"`
- `test_create_folder_rejects_quotes_and_backslashes` — `ValueError` on `"Bad\"Folder"`
- `test_create_folder_rejects_path_traversal` — `ValueError` on `"../Other"`
- `test_create_folder_rejects_leading_delimiter` — `ValueError` on `"/Absolute"`
- `test_create_folder_rejects_inbox` — `ValueError` on `"INBOX"`
- `test_create_folder_rejects_empty_name` — `ValueError` on `""`
- `test_create_folder_rejects_deep_nesting` — `ValueError` on 11-level path
- `test_create_folder_rejects_too_long` — `ValueError` on 256-byte name
- `test_create_folder_already_exists` — `RuntimeError` on `NO [ALREADYEXISTS]`
- `test_create_folder_permission_denied` — `RuntimeError` on `NO [NOPERM]`
- `test_create_folder_generic_no_response` — `RuntimeError` on generic `NO`
- `test_create_folder_uses_operation_lock`

### 8.2 Sync Wrapper Tests
- `test_create_folder_delegates_to_async_client`
- `test_create_folder_returns_true_on_success`
- `test_create_folder_wraps_errors`

### 8.3 MCP Tool Tests
- `test_create_folder_tool_success`
- `test_create_folder_tool_account_not_found`
- `test_create_folder_tool_rate_limited`
- `test_create_folder_tool_logs_via_ctx`
- `test_create_folder_tool_propagates_sanitization_error` (crlf)
- `test_create_folder_tool_rejects_quote_in_name`
- `test_create_folder_tool_rejects_inbox_name`
- `test_create_folder_tool_rejects_traversal`
- `test_create_folder_tool_calls_audit_log`
- `test_create_folder_tool_already_exists`
- `test_create_folder_tool_permission_denied`

---

## 9. Decision Log

| Decision | Rationale | Disagreement Resolution |
|----------|-----------|------------------------|
| Adopt security engineer's input validation | State-changing operation needs defense-in-depth | API architect proposed lighter validation; security's blocking findings H01/H02 take precedence |
| Map IMAP errors to generic static messages | Prevent information disclosure | API architect proposed richer error messages; security engineer's generic mapping adopted |
| Add audit logging | State-changing operations need forensic trail | API architect didn't require it; security engineer's M04 finding adopted |
| Defer separate write rate limiter | Avoid scope creep for a single tool | Security engineer recommended it (H03); agreed to implement shared limiter for now, enhance later |
| Treat both `/` and `.` as delimiters | Delimiter unknown at validation time | Pragmatic compromise: validate against both |

---

## 10. Approval

- **API Architect**: Approved with security validation additions
- **Security Engineer**: Approved with consensus validation rules
- **Project Manager**: Consensus reached, proceeding to implementation

---

*Next step: Phase 2.5 — Create test stubs, then Phase 4 — Implementation*
