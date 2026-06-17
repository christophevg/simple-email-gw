# P1-001 Consensus Implementation Plan

**Date**: 2026-06-17
**Task**: P1-001 - Add IMAP append tool and auto-save Sent folder support
**Status**: Owner approved and implemented

This document reconciles the API design review (`analysis/api-p1-001.md`) and the security review (`analysis/security-p1-001.md`) into a single implementation plan. Conflicts that required resolution are called out explicitly.

## 1. Resolved Conflicts

| Conflict | API Review Position | Security Review Position | Consensus Resolution |
|----------|---------------------|--------------------------|----------------------|
| `append_email` tool input encoding | Base64-encoded RFC822 `raw_message` preserves bytes exactly | Raw RFC822 `message` content with header re-parsing | **Base64 input + sanitization**: tool accepts base64, decodes to bytes, re-parses headers, and applies existing sanitizers before APPEND. |
| IMAP client append method name | `append_email()` | `append_message()` | **`append_message()` in `IMAPClient`**, `append_email()` reserved for the MCP tool. Avoids naming collision and clarifies layers. |
| SMTP auto-append parameter names | `append_to_sent`, `append_folder` | `save_to_sent`, `sent_folder` | **Keep `append_to_sent` and `append_folder`** because they match the acceptance criteria and existing TODO.md wording. |
| APPEND flags | `list[str] \| None` with examples | Strict allowlist: `\Seen`, `\Draft`, `\Answered`, `\Flagged` | **Keep `list[str] \| None` signature but validate against the allowlist** at both MCP and IMAP layers. |
| `internal_date` parameter | Not included | Include optional `internal_date` for CRLF safety | **Include in `IMAPClient.append_message()` as a timezone-aware `datetime \| None`**, but **do not expose in the MCP tool** until required. This closes the CRLF injection vector without expanding the tool surface. |

No other substantive conflicts were identified. Both reviews agree on: non-blocking auto-append, Sent folder detection via `\Sent` special-use flag, Message-ID generation before SMTP submission, structured append warnings, and generic IMAP error mapping.

## 2. Final Agreed Tool Signatures

### 2.1 MCP Tool: `append_email`

```python
@mcp.tool
async def append_email(
    account: Annotated[str, Field(description="Account name")],
    folder: Annotated[str, Field(default="Sent", description="Destination folder")] = "Sent",
    raw_message: Annotated[str, Field(description="Base64-encoded RFC822 message")],
    flags: Annotated[
        list[str] | None,
        Field(default=None, description="Optional IMAP flags such as [\\Seen]")
    ] = None,
    ctx: Context | None = None,
) -> dict[str, str]
```

**Returns**:

```json
{
  "status": "appended",
  "folder": "Sent"
}
```

**Validation**:

| Input | Rule | Failure Action |
|-------|------|----------------|
| `account` | Must exist in `get_accounts()` | `ToolError("Account not found: ...")` |
| `folder` | `validate_folder_name(folder)` then `sanitize_folder_name(folder)` | `ToolError` with validation message |
| `raw_message` | Valid base64; decode to bytes; reject empty; enforce max size; reject NUL; re-parse headers and sanitize | `ToolError("Invalid message content")` |
| `flags` | Each flag must be in `AppendFlags.ALL` | `ToolError("Invalid IMAP flag")` |

### 2.2 MCP Tool: `send_email` (updated)

Add two optional parameters:

```python
append_to_sent: Annotated[bool, Field(default=False, description="Append a copy to the Sent folder after sending")] = False,
append_folder: Annotated[str | None, Field(default=None, description="Override destination folder for auto-append")] = None,
```

The tool obtains both SMTP and IMAP clients from the pool and passes the IMAP client to `SMTPClient.send_email`.

### 2.3 MCP Tool: `reply_email` (updated)

Same two parameters as `send_email`:

```python
append_to_sent: Annotated[bool, Field(default=False, description="Append a copy to the Sent folder after sending")] = False,
append_folder: Annotated[str | None, Field(default=None, description="Override destination folder for auto-append")] = None,
```

### 2.4 IMAP Client: `find_sent_folder`

```python
async def find_sent_folder(self) -> str | None:
    """Return the account's Sent folder name.

    Uses the IMAP \Sent special-use flag if advertised; otherwise tries
    common local names in a documented, deterministic order.

    Returns:
      Sent folder name, or None if no candidate is found.
    """
```

Implementation:

- Scan `list_folders()` for a flag equal to `\Sent` (case-insensitive match on `\SENT`).
- If no special-use flag is found, fall back to well-known names: `Sent`, `Sent Items`, `Sent Messages`.
- Return `None` when no candidate exists.

### 2.5 IMAP Client: `append_message`

```python
async def append_message(
    self,
    folder: str,
    message_bytes: bytes,
    flags: list[str] | None = None,
    internal_date: datetime | None = None,
) -> dict[str, str]:
    """Append a message to an IMAP folder.

    Args:
      folder: Target folder name (e.g., "Sent").
      message_bytes: RFC822 message as bytes.
      flags: Optional IMAP flags from the allowlist.
      internal_date: Optional timezone-aware datetime for the IMAP internal date.

    Returns:
      Dict with 'status' and 'folder' keys.

    Raises:
      ValueError: If folder name, flags, or message content is invalid.
      RuntimeError: If the IMAP server rejects APPEND.
    """
```

### 2.6 SMTP Client: `send_email` (updated)

```python
async def send_email(
    self,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
    append_to_sent: bool = False,
    append_folder: str | None = None,
    imap_client: IMAPClient | None = None,
) -> dict[str, str | bool | None]
```

### 2.7 SMTP Client: `reply_email` (updated)

```python
async def reply_email(
    self,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str,
    references: list[str] | None = None,
    html_body: str | None = None,
    append_to_sent: bool = False,
    append_folder: str | None = None,
    imap_client: IMAPClient | None = None,
) -> dict[str, str | bool | None]
```

### 2.8 Sync Wrappers

`SyncIMAPClient` exposes:

```python
def find_sent_folder(self) -> str | None: ...

def append_message(
    self,
    folder: str,
    message_bytes: bytes,
    flags: list[str] | None = None,
    internal_date: datetime | None = None,
) -> dict[str, str]: ...
```

`SyncSMTPClient.send_email` and `reply_email` mirror the async signatures, accepting an optional `SyncIMAPClient` instance that is passed through to the async `SMTPClient`.

### 2.9 Return Shape for `send_email` / `reply_email`

On SMTP success:

```json
{
  "status": "sent",
  "recipients": "alice@example.com",
  "message": "OK",
  "appended": true,
  "append_folder": "Sent",
  "append_warning": null
}
```

When append is disabled, fails, or no Sent folder is found:

```json
{
  "status": "sent",
  "recipients": "alice@example.com",
  "message": "OK",
  "appended": false,
  "append_folder": null,
  "append_warning": "Could not save copy to Sent folder"
}
```

The `append_warning` value must be a static, user-safe string. Raw exception text or IMAP server responses are never returned to the MCP client.

## 3. File Changes Required

| File | Change |
|------|--------|
| `src/simple_email_gw/imap/client.py` | Add `find_sent_folder()` and `append_message()`; add flag allowlist helper; add `_decode_append_error()` for generic IMAP error mapping. |
| `src/simple_email_gw/imap/sync_client.py` | Add sync wrappers for `find_sent_folder()` and `append_message()`. |
| `src/simple_email_gw/smtp/client.py` | Generate `Message-ID` before submission; add `append_to_sent`, `append_folder`, and `imap_client` parameters to `send_email` and `reply_email`; implement non-blocking append path. |
| `src/simple_email_gw/smtp/sync_client.py` | Mirror new parameters and accept optional `SyncIMAPClient`. |
| `src/simple_email_gw/safety/sanitize.py` | Add `validate_append_flags()` helper enforcing the flag allowlist. |
| `src/simple_email_gw/safety/audit.py` | Add `log_email_appended()` for all APPEND operations. |
| `src/simple_email_gw/mcp.py` | Add `append_email` tool; update `send_email` and `reply_email` tool signatures and calls. |
| `src/simple_email_gw/__init__.py` | Export new public helpers if applicable. |
| `README.md` | Add `append_email` to MCP tools table; document auto-append options. |
| `tests/test_imap_client.py` | Test `find_sent_folder`, `append_message`, flag validation, size limits, error mapping, audit logging. |
| `tests/test_smtp_client.py` | Test append path success/failure, Message-ID preservation, non-blocking behavior. |
| `tests/test_mcp.py` | Test `append_email` tool and auto-append params. |
| `tests/test_sanitize.py` | Test append flag validation. |
| `tests/test_audit.py` | Test `log_email_appended()` invocation and content. |

## 4. Implementation Steps in Order

1. **Add security helpers**
   - `src/simple_email_gw/safety/sanitize.py`: add `validate_append_flags()` returning the allowlist `{"\Seen", "\Draft", "\Answered", "\Flagged"}`.
   - `src/simple_email_gw/safety/audit.py`: add `log_email_appended()`.

2. **Extend IMAP client**
   - Add constant `APPEND_FLAG_ALLOWLIST` and module-level helper `_validate_append_flags()`.
   - Implement `find_sent_folder()` using `\Sent` special-use flag with deterministic fallback.
   - Implement `append_message()` with folder validation, flag allowlist, NUL/size checks, internal-date type check, generic error mapping, and audit logging.

3. **Extend SMTP client**
   - Generate stable `Message-ID` with `email.utils.make_msgid()` before calling `_send()`.
   - Add `append_to_sent`, `append_folder`, and `imap_client` parameters to `send_email` and `reply_email`.
   - After successful SMTP send, if `append_to_sent` is true:
     - Resolve target folder (`append_folder` or `await imap_client.find_sent_folder()`).
     - Serialize the same message object with `msg.as_bytes()`.
     - Enforce max message size.
     - Call `imap_client.append_message(folder, message_bytes, flags=["\Seen"])`.
     - On any exception, log a warning and set a safe `append_warning` in the result.
   - Return the merged result dict with `appended`, `append_folder`, and `append_warning`.

4. **Add sync wrappers**
   - `SyncIMAPClient.find_sent_folder()` and `append_message()`.
   - `SyncSMTPClient.send_email()` and `reply_email()` updated signatures with `SyncIMAPClient` injection.

5. **Update MCP layer**
   - Add `append_email` tool that decodes base64, re-parses/sanitizes message headers, validates folder and flags, enforces size limit, and calls `IMAPClient.append_message()`.
   - Update `send_email` MCP tool with `append_to_sent` and `append_folder`; obtain both SMTP and IMAP clients from pool and pass IMAP client to `SMTPClient.send_email()`.
   - Update `reply_email` MCP tool the same way.

6. **Documentation**
   - Update `README.md` MCP tools table and add auto-append usage examples.

7. **Tests**
   - Unit tests for new helpers.
   - Client tests for success, failure, fallback, and header preservation.
   - MCP tool tests for validation, happy path, and error mapping.

## 5. How API and Security Recommendations Are Reconciled

### 5.1 Base64 Input + Sanitization

The API review advocated for base64-encoded input because it avoids reconstructing MIME and preserves all headers exactly. The security review required re-parsing and header sanitization to prevent stored header injection. The consensus is to **accept base64, decode it, re-parse with `email.message_from_bytes()`, and validate/sanitize the envelope/threading headers using the existing `sanitize_message_id()`, `sanitize_references()`, and `sanitize_subject()` helpers**. This preserves the exact byte content for the APPEND literal while still rejecting CRLF/NUL injection in the headers that downstream tools trust.

### 5.2 IMAP Method Naming

The API review used `append_email()` for both the IMAP client method and the MCP tool. The security review used `append_message()` for the IMAP client to distinguish it from the tool. The consensus names the low-level client method `append_message()` and keeps the user-facing MCP tool as `append_email()`, matching the task name and avoiding confusion between protocol handler and tool surface.

### 5.3 Auto-Append Parameter Names

The security review suggested `save_to_sent` / `sent_folder`, while the API review and the existing acceptance criteria use `append_to_sent` / `append_folder`. The consensus keeps the acceptance-criteria names (`append_to_sent`, `append_folder`) for traceability.

### 5.4 Flags Allowlist

The API review left flags open-ended. The security review required an allowlist. The consensus keeps the flexible `list[str] | None` type but validates every flag against `{"\Seen", "\Draft", "\Answered", "\Flagged"}` at both the MCP tool and the IMAP client layers.

### 5.5 Internal Date

The security review identified CRLF injection risk in an optional `internal_date` string. The consensus accepts `internal_date` only as a timezone-aware `datetime` object inside `IMAPClient.append_message()`, eliminating command-line string injection. The MCP `append_email` tool does not expose this parameter, minimizing tool surface until a concrete use case requires it.

### 5.6 Error Message Hygiene

Both reviews agree that raw IMAP server text must not reach the MCP client. The consensus uses the API review's structured response fields (`appended`, `append_folder`, `append_warning`) and populates `append_warning` with static, safe strings. Server-specific details are logged internally at `WARNING` or `DEBUG` level.

### 5.7 Message Size Cap

The API review focused on byte preservation; the security review required a size cap. The consensus enforces a default 25 MB maximum for appended messages, configurable via `EMAIL_APPEND_MAX_SIZE`, and rejects oversized input before issuing IMAP commands.

### 5.8 Audit Logging

The API review mentioned audit logging but did not specify details. The security review provided a concrete `log_email_appended()` function. The consensus adopts the security review's function and calls it on every successful direct append, every successful auto-append, and every failed auto-append (with `success=False`).

## 6. Acceptance Criteria Checklist

These map to the acceptance criteria already recorded in `TODO.md` for P1-001.

- [ ] 1. New `append_email` MCP tool performs pure IMAP APPEND.
- [ ] 2. `send_email` supports optional auto-append to Sent folder, default `False`.
- [ ] 3. `send_email` supports optional folder override for auto-append destination.
- [ ] 4. `reply_email` supports the same auto-append and folder-override options.
- [ ] 5. `Message-Id`, `References`, and `In-Reply-To` headers are preserved in the appended copy.
- [ ] 6. SMTP send succeeds even if append fails; append failure surfaces as a safe warning in the response.
- [ ] 7. No `copy_email` tool is added.
- [ ] 8. Sent folder is detected via the IMAP `\Sent` special-use flag, with deterministic fallback to common names.
- [ ] 9. Tests and README documentation are added.

### Security-specific acceptance criteria

- [ ] 10. Destination folder names pass `validate_folder_name()` / `sanitize_folder_name()` at both MCP and IMAP layers.
- [ ] 11. Caller-supplied message content is base64-decoded, re-parsed, and envelope/threading headers are sanitized before APPEND.
- [ ] 12. APPEND flags are restricted to the allowlist `\Seen`, `\Draft`, `\Answered`, `\Flagged`.
- [ ] 13. Optional `internal_date` is accepted only as a timezone-aware `datetime` object.
- [ ] 14. Appended message size is capped at a configurable maximum (default 25 MB).
- [ ] 15. Every APPEND operation is recorded by `log_email_appended()`.
- [ ] 16. IMAP APPEND errors are mapped to generic user-facing messages; raw server text is never returned to MCP clients.

## 7. Pending Decision / Owner Approval

This consensus plan was reviewed and approved by the repository owner. Implementation has been completed on branch `feature/p1-001-imap-append-sent`.

Per owner feedback during review, the following additions were also made:

- **CLI support**: The `append_email` functionality is exposed through the CLI, and the `send` / `reply` commands support `--append-to-sent` and `--append-folder` options.
- **Documentation**: `README.md` was updated with the new MCP tools, CLI examples, and auto-append usage guidance.

All acceptance criteria listed in section 6 have been implemented and verified by CI.
