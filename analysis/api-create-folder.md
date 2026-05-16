# API Design: create_folder MCP Tool and IMAP Client Method

**Date**: 2026-05-16
**Task**: MCP-001 - Add `create_folder` tool
**Context**: Design only (no implementation)

---

## 1. Summary

Add a `create_folder` capability to the simple-email-gw project, exposing it both as an MCP tool (`mcp.py`) and as an async IMAP client method (`imap/client.py`). The design follows existing patterns for tool structure, error handling, sanitization, and connection pool usage. It also extends the sync wrapper (`SyncIMAPClient`) to maintain parity with existing client methods.

---

## 2. Proposed `IMAPClient.create_folder()` Method

### 2.1 Signature

```python
async def create_folder(self, folder_name: str) -> bool:
    """Create a new folder/mailbox on the IMAP server.

    Args:
      folder_name: Name of the folder to create.

    Returns:
      True if the folder was created successfully.

    Raises:
      ValueError: If folder name contains invalid characters.
      RuntimeError: If the IMAP server rejects the CREATE command
                    (e.g., folder already exists, permission denied).
    """
```

### 2.2 Implementation Approach

Follow the exact pattern used by `select_folder`, `search`, and `move_message`:

1. **Sanitize input** via `sanitize_folder_name(folder_name)` to prevent CRLF injection.
2. **Acquire `self._operation_lock`** to serialize IMAP commands on the connection.
3. **Call `await self.connect()`** to ensure a live connection.
4. **Invoke `await client.create(safe_folder)`** using `aioimaplib`.
5. **Inspect response**:
   - `status == "OK"`: return `True`
   - `status == "NO"`: parse server response text and raise `RuntimeError` with a user-friendly message.
6. **No SELECT needed** after CREATE (RFC 3501 does not auto-select created mailboxes).

```python
async def create_folder(self, folder_name: str) -> bool:
    safe_folder = sanitize_folder_name(folder_name)
    async with self._operation_lock:
        client = await self.connect()
        status, data = await client.create(safe_folder)
        if status == "OK":
            return True
        # Parse NO response for specific error messages
        error_text = ""
        if data and isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, bytes):
                error_text = first.decode(errors="replace")
            elif isinstance(first, str):
                error_text = first
        raise RuntimeError(f"Failed to create folder: {error_text or status}")
```

### 2.3 Error Mapping (IMAP -> Python)

| IMAP Response / Server Text | Exception Type | Message |
|----------------------------|----------------|---------|
| `NO [ALREADYEXISTS] Mailbox already exists` | `RuntimeError` | `Folder already exists: {folder_name}` |
| `NO [NOPERM] Permission denied` | `RuntimeError` | `Permission denied: cannot create folder {folder_name}` |
| `NO Invalid mailbox name` | `RuntimeError` | `Invalid folder name: {folder_name}` |
| Generic `NO` response | `RuntimeError` | `Failed to create folder: {status/text}` |
| `sanitize_folder_name` detects `\r` or `\n` | `ValueError` | `Folder name contains invalid characters` |

> **Note**: The existing codebase wraps IMAP errors in `RuntimeError` with descriptive text rather than introducing new exception classes. This design preserves that consistency.

---

## 3. Proposed MCP Tool

### 3.1 Signature

```python
@mcp.tool
async def create_folder(
    account: Annotated[str, Field(description="Account name")],
    folder_name: Annotated[str, Field(description="Name of the folder to create")],
    ctx: Context | None = None,
) -> dict[str, str]:
    """Create a new folder/mailbox on the email account.

    Args:
      account: The account name.
      folder_name: The name of the new folder.

    Returns:
      Dictionary with status and folder name.
    """
```

### 3.2 Implementation Approach

Follow the `list_folders` / `move_email` / `delete_email` pattern exactly:

1. **Log intent** via `ctx.info(f"Creating folder {folder_name} for account: {account}")`.
2. **Get pool** and **IMAP client**.
3. **Delegate** to `client.create_folder(folder_name)`.
4. **Return** `{"status": "created", "folder": folder_name}`.
5. **Exception handling**:
   - `ValueError` -> `ToolError(f"Account not found: {account}")` or pass-through from sanitization.
   - `RateLimitError` -> `ToolError("Rate limit exceeded. Please try again later.")`.
   - `RuntimeError` (from IMAP NO) -> `ToolError(str(e))`.
   - Generic `Exception` -> `ToolError("Failed to create folder. Check server logs for details.")`.

```python
@mcp.tool
async def create_folder(
    account: Annotated[str, Field(description="Account name")],
    folder_name: Annotated[str, Field(description="Name of the folder to create")],
    ctx: Context | None = None,
) -> dict[str, str]:
    """Create a new folder/mailbox on the email account."""
    if ctx:
        await ctx.info(f"Creating folder {folder_name} for account: {account}")

    try:
        pool = await get_pool()
        client = await pool.get_imap_client(account)
        await client.create_folder(folder_name)
        return {"status": "created", "folder": folder_name}
    except ValueError as e:
        # Distinguish account-not-found from sanitization errors
        msg = str(e)
        if "Account not found" in msg or "not found" in msg.lower():
            raise ToolError(f"Account not found: {account}")
        raise ToolError(msg)
    except RateLimitError:
        raise ToolError("Rate limit exceeded. Please try again later.")
    except RuntimeError as e:
        raise ToolError(str(e))
    except Exception:
        raise ToolError("Failed to create folder. Check server logs for details.")
```

> **Note**: In the existing codebase, `ValueError` is raised by the pool when an account is not found. `sanitize_folder_name` also raises `ValueError`. The tool-level handler should inspect the message to provide an accurate user-facing error. Alternatively, the `IMAPClient.create_folder` method could catch the `ValueError` from sanitization and re-raise a more specific exception, but the current project pattern is to let `ValueError` bubble up and handle it at the tool layer.

---

## 4. Sync Wrapper Extension (`SyncIMAPClient`)

To maintain parity with all other public methods on `IMAPClient`, add a synchronous wrapper in `imap/sync_client.py`:

```python
def create_folder(self, folder_name: str) -> bool:
    """Create a new folder/mailbox.

    Args:
      folder_name: Name of the folder to create

    Returns:
      True if successful

    Raises:
      RuntimeError: If operation fails
      ValueError: If folder name contains invalid characters
    """
    return self._run_coroutine(
        self._async_client.create_folder(folder_name)
    )  # type: ignore[no-any-return]
```

---

## 5. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| CRLF injection in folder name | `sanitize_folder_name()` strips `\r` and `\n` and raises `ValueError` if present. |
| Path traversal via folder name | IMAP CREATE operates on mailbox namespaces, not filesystem paths. The `aioimaplib` library handles protocol-level quoting. No additional path sanitization is required beyond CRLF. |
| Information leakage | Error messages should NOT include raw server responses that might expose internal paths or account structure. The proposed implementation uses a controlled `RuntimeError` with generic but descriptive text. |
| Rate limiting | The connection pool already applies per-account rate limiting via `imap_limiter`. The tool inherits this protection. |
| Re-creation of existing folders | The IMAP `ALREADYEXISTS` response will be surfaced to the user as a clear `ToolError`. No automatic overwrite or deletion occurs. |

---

## 6. Tests That Should Be Written

### 6.1 Async IMAP Client Tests (`tests/test_imap_client.py`)

- **test_create_folder_success**
  - Mock `client.create` returning `("OK", [b"Created"])`
  - Assert `create_folder("Archive")` returns `True`
  - Assert `sanitize_folder_name` is called with `"Archive"`

- **test_create_folder_sanitization_rejects_crlf**
  - Pass `"Bad\r\nFolder"`
  - Assert `ValueError` is raised with message matching `invalid characters`

- **test_create_folder_already_exists**
  - Mock `client.create` returning `("NO", [b"[ALREADYEXISTS] Mailbox already exists"])`
  - Assert `RuntimeError` is raised with message matching `already exists`

- **test_create_folder_permission_denied**
  - Mock `client.create` returning `("NO", [b"[NOPERM] Permission denied"])`
  - Assert `RuntimeError` is raised with message matching `Permission denied`

- **test_create_folder_generic_no_response**
  - Mock `client.create` returning `("NO", [])`
  - Assert `RuntimeError` is raised with a generic failure message

- **test_create_folder_uses_operation_lock**
  - Verify that `self._operation_lock` is acquired during the call

### 6.2 Sync Wrapper Tests (`tests/test_sync_imap_client.py`)

- **test_create_folder_delegates_to_async_client**
  - Patch `async_client.create_folder` to return `True`
  - Assert sync wrapper delegates with correct argument

- **test_create_folder_returns_true_on_success**
  - Same setup, assert return value is `True`

- **test_create_folder_wraps_errors**
  - Patch async side to raise `RuntimeError`
  - Assert sync wrapper raises `RuntimeError` with matching text

### 6.3 MCP Tool Tests (new file or existing suite)

- **test_create_folder_tool_success**
  - Mock `pool.get_imap_client` and `client.create_folder`
  - Assert tool returns `{"status": "created", "folder": "Archive"}`

- **test_create_folder_tool_account_not_found**
  - Mock pool to raise `ValueError("Account not found: missing")`
  - Assert `ToolError` with text matching `Account not found`

- **test_create_folder_tool_rate_limited**
  - Mock pool to raise `RateLimitError`
  - Assert `ToolError` with text matching `Rate limit exceeded`

- **test_create_folder_tool_logs_via_ctx**
  - Pass a mock `Context`
  - Assert `ctx.info` is called with the folder/account name

- **test_create_folder_tool_propagates_sanitization_error**
  - Pass `folder_name="Bad\r\nFolder"`
  - Assert `ToolError` is raised with message matching `invalid characters`

---

## 7. Files to Modify

| File | Change |
|------|--------|
| `src/simple_email_gw/imap/client.py` | Add `create_folder()` async method to `IMAPClient` |
| `src/simple_email_gw/imap/sync_client.py` | Add `create_folder()` sync wrapper to `SyncIMAPClient` |
| `src/simple_email_gw/mcp.py` | Add `create_folder` MCP tool function |
| `tests/test_imap_client.py` | Add async client tests for `create_folder` |
| `tests/test_sync_imap_client.py` | Add sync wrapper tests for `create_folder` |

---

## 8. OpenAPI / Interface Notes

This is an internal MCP tool, not an HTTP REST endpoint, so no OpenAPI path is required. The tool contract is:

- **Input**: `account` (string), `folder_name` (string)
- **Output**: JSON object `{"status": "created", "folder": "<name>"}`
- **Errors**: Raised as `ToolError` with human-readable string messages

---

## 9. Action Items

1. Implement `IMAPClient.create_folder()` in `src/simple_email_gw/imap/client.py`
2. Implement `SyncIMAPClient.create_folder()` in `src/simple_email_gw/imap/sync_client.py`
3. Implement `create_folder` MCP tool in `src/simple_email_gw/mcp.py`
4. Write unit tests for async client, sync wrapper, and MCP tool
5. Update `TODO.md` to mark MCP-001 as complete
