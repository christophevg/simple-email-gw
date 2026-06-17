# Security Analysis: IMAP Append Tool and Sent Folder Auto-Save (P1-001)

## Security Review Report

### Executive Summary

Task P1-001 adds an `append_email` MCP tool that performs raw IMAP APPEND of a complete RFC 5322 message, and extends `send_email`/`reply_email` to optionally auto-save a copy to the account's Sent folder. The security surface is larger than prior folder tools because it combines IMAP command framing (folder name, flags, internal date), untrusted MIME content, and cross-client coordination between SMTP and IMAP. The existing `validate_folder_name()` and `sanitize_*` helpers provide a strong baseline, but APPEND introduces new injection vectors in the message literal boundary, header preservation, and the auto-append warning/fallback path. This analysis provides a STRIDE threat model, required validation rules, audit logging requirements, and test scenarios.

---

### Threat Model: `append_email` and Auto-Append

#### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Client / LLM Agent (untrusted input)                          │
│  - account, folder, message (MIME), flags, date                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Server (mcp.py)                                               │
│  - Pydantic field validation                                         │
│  - Account existence check via connection pool                       │
│  - Folder validation, Message-Id/header sanitization                 │
│  - Error mapping to ToolError                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SMTP Client (smtp/client.py) — auto-append path only              │
│  - Builds/sends RFC 5322 message                                    │
│  - Captures generated Message-Id, References, In-Reply-To             │
│  - Calls IMAP append after send; treats failure as warning           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  IMAP Client (imap/client.py)                                      │
│  - folder validation + CRLF checks                                    │
│  - append_message() protocol handling                                 │
│  - Operation-level locking                                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Connection Pool (connections/pool.py)                               │
│  - Rate limiting (60 req/min IMAP, 100/hr SMTP)                     │
│  - Client lifecycle management                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  IMAP Server (external trust boundary)                               │
│  - Namespace isolation, ACL enforcement, APPEND quota                │
└─────────────────────────────────────────────────────────────────────┘
```

#### STRIDE Threat Analysis

| STRIDE | Threat | Risk | Mitigation Status |
|--------|--------|------|-------------------|
| **Spoofing** | Attacker appends a message to a folder the user did not intend (e.g., INBOX or Trash) by manipulating the `folder` argument or auto-append detection | Medium | Partial: folder sanitization exists; special-use flag detection needs verification |
| **Tampering** | IMAP APPEND command injection via folder name, flag string, or internal date containing CRLF or unquoted IMAP metacharacters | **High** | Partial: `validate_folder_name()` blocks many metacharacters, but APPEND-specific flags/date need separate validation |
| **Tampering** | Appended MIME message contains injected headers (Bcc, Subject, From) because raw RFC 5322 content is accepted without header sanitization | **High** | **Gap**: raw message content is currently unvalidated |
| **Repudiation** | APPEND operations are not audited; cannot reconstruct who appended what or detect abuse | Medium | **Gap**: no `log_email_appended()` audit function |
| **Information Disclosure** | Sensitive headers (Message-Id, recipient addresses, subject) from appended messages leak into audit logs or error messages | Medium | Partial: existing `log_email_sent()` truncates subject/recipients; same discipline needed |
| **Denial of Service** | Huge MIME messages exhaust IMAP quota, memory, or bandwidth | **High** | **Gap**: no message size cap or body parsing limit |
| **Denial of Service** | Rapid APPEND calls fill Sent folder or quota despite rate limiting | Medium | Partial: 60 req/min IMAP limit exists but no APPEND-specific quota check |
| **Elevation of Privilege** | Auto-append creates folders implicitly; combined with folder override could create unexpected mailboxes outside namespace | Low | Partial: `validate_folder_name()` rejects traversal and leading delimiters |

---

### Critical Findings (CVSS 9.0–10.0)

None identified. The highest risks are High severity because exploitation depends on bypassing multiple layers and because the IMAP server ultimately enforces namespace/ACL boundaries.

---

### High Findings (CVSS 7.0–8.9)

#### H01: CRLF Injection in IMAP APPEND Framing (CVSS 8.1)

- **Vulnerability**: IMAP APPEND sends the target mailbox, optional flag list, optional internal date, and a message literal. The current `sanitize_folder_name()` only rejects `\r`/`\n` and IMAP metacharacters, which is good for the mailbox argument. However, if the implementation constructs an APPEND command line manually (e.g., `APPEND "folder" (\Seen) "date" {size}`), untrusted `flags` or `internal_date` arguments containing CRLF could terminate the command early and inject a new IMAP command before the literal is sent.
- **OWASP A05 (Injection)**
- **Impact**: An attacker could inject arbitrary IMAP commands into the same authenticated session, such as `APPEND Sent (\Seen) "17-May-2026" {0}\r\nNOOP\r\n`, causing the server to execute `NOOP` or worse. Even if `aioimaplib` uses literals for the message body, command-line arguments before the literal must still be sanitized.
- **Remediation**:
  1. Never accept arbitrary flag strings from the MCP tool. If `append_email` exposes flags, restrict them to a small allowlist (e.g., `\Seen`, `\Draft`, `\Answered`, `\Flagged`).
  2. If an internal date is accepted, parse it strictly with `email.utils.parsedate_to_datetime()` and reject any string containing `\r`, `\n`, or double quotes; emit only RFC 3501 date-time format.
  3. Prefer `aioimaplib`'s high-level append helper if it accepts Python `email.message.Message` objects and handles literal framing internally. Verify with a test that CRLF in the supplied message body is treated as data, not protocol.
  4. Add an `append_message()` helper in `imap/client.py` that validates the folder, validates optional flags/date, and passes the message bytes to the library without manual string concatenation.
- **Reference**: [RFC 3501 Section 6.3.11 - APPEND](https://datatracker.ietf.org/doc/html/rfc3501#section-6.3.11); CWE-93 (Improper Neutralization of CRLF Sequences)
- **Classification**: **Blocking** — must be fixed before P1-001 is complete.

#### H02: Untrusted Raw MIME Content Allows Header Injection (CVSS 8.1)

- **Vulnerability**: The `append_email` tool accepts a full RFC 5322 message. If the implementation passes the caller-supplied bytes directly to the IMAP server, malicious MIME content can contain arbitrary headers (`Bcc:`, `From:`, `Subject:`, `Date:`, etc.) that are stored verbatim and later returned by `fetch_message`. Because the gateway's own `send_email` sanitizes headers, a raw append path that bypasses those checks creates an inconsistency and a stored-header-injection vector.
- **OWASP A05 (Injection)** / A08 (Software/Data Integrity)
- **Impact**: An attacker can plant messages in the user's mailbox with spoofed sender, subject, or threading headers. Downstream tools (search, reply, display) may trust these headers, leading to phishing content in the mailbox, thread confusion, or false context for LLM agents.
- **Remediation**:
  1. For the `append_email` MCP tool, accept message content but **re-parse it** with `email.message_from_bytes()` and reject messages whose `From`, `To`, `Subject`, `Message-Id`, `In-Reply-To`, or `References` headers contain CRLF or null bytes.
  2. Apply the existing `sanitize_message_id()`, `sanitize_references()`, and `sanitize_subject()` helpers to the parsed headers. Do **not** allow injecting a `Bcc` header unless the caller is the account owner and the tool explicitly documents that behavior.
  3. Strip or reject any headers that are not standard RFC 5322 envelope headers (e.g., `X-`* headers are acceptable but should be listed in audit logs).
  4. For the auto-append path, use the same `EmailMessage` object already built and sanitized by `SMTPClient.send_email()` / `reply_email()`; do not re-serialize and re-parse in a way that re-interprets headers.
- **Reference**: CWE-93, CWE-346 (Origin Validation Error)
- **Classification**: **Blocking** — must be fixed before P1-001 is complete.

#### H03: Denial of Service via Large Appended Messages (CVSS 7.5)

- **Vulnerability**: IMAP APPEND stores the entire message on the server. There is no upper bound on message size in the current client or MCP layer. An attacker (or a buggy LLM) can append multi-megabyte or multi-gigabyte payloads, consuming IMAP quota, server storage, and local memory during serialization.
- **OWASP A06 (Insecure Design) / A09**
- **Impact**: Mailbox quota exhaustion blocks legitimate mail delivery. Large literals may also trigger server timeouts or memory pressure in the gateway process.
- **Remediation**:
  1. Add a configurable maximum message size (default 25 MB) and reject `append_email` calls that exceed it before issuing IMAP commands.
  2. For auto-append, use the same size check on the serialized message before APPEND.
  3. Expose the limit as an environment variable (e.g., `EMAIL_APPEND_MAX_SIZE`) so deployments can tighten it.
  4. Count APPEND against a separate IMAP state-change rate limit or at least document that the existing 60 req/min limit applies.
- **Reference**: CWE-400 (Uncontrolled Resource Consumption)
- **Classification**: **Related** — should be addressed as part of P1-001 implementation.

---

### Medium Findings (CVSS 4.0–6.9)

#### M01: Missing Audit Logging for APPEND Operations (CVSS 5.3)

- **Vulnerability**: `safety/audit.py` has `log_email_sent()` but no equivalent for IMAP APPEND. The new `append_email` tool and the auto-append code path in `send_email`/`reply_email` will modify mailbox state without an audit trail.
- **OWASP A09 (Security Logging Failures)**
- **Impact**: No forensic record if an attacker appends phishing messages, if auto-append misbehaves, or if quota is exhausted by abuse.
- **Remediation**:
  1. Add `log_email_appended(account: str, folder: str, subject_prefix: str, message_size: int, auto_append: bool = False)` to `safety/audit.py`.
  2. Call it from `IMAPClient.append_message()` on success and from the MCP `append_email` tool wrapper.
  3. For auto-append, call it from `SMTPClient.send_email()` / `reply_email()` only when the append succeeds, with `auto_append=True`.
  4. Include the destination folder and the first 50 characters of the subject (already sanitized) but never full recipient lists or message bodies.
- **Classification**: **Blocking** — required for P1-001 because audit logging is a documented project security feature.

#### M02: Information Disclosure via APPEND Error Messages (CVSS 5.3)

- **Vulnerability**: IMAP server APPEND errors may include the mailbox path, quota details, or server internals (e.g., `[OVERQUOTA]`, `[NOPERM]`, `[TRYCREATE]`). If these strings propagate through `ToolError`, they may be exposed to the MCP client and LLM context.
- **OWASP A04 (Cryptographic Failures — Information Disclosure)**
- **Impact**: Reconnaissance aid for further attacks; leakage of internal server configuration.
- **Remediation**:
  1. In `IMAPClient.append_message()`, catch `aioimaplib.Error` and raise generic `RuntimeError("Failed to append message. Check server logs for details.")`.
  2. Map known response codes to safe user-facing strings: `[OVERQUOTA]` -> "Mailbox quota exceeded", `[NOPERM]` -> "Permission denied", `[TRYCREATE]` -> "Folder does not exist".
  3. Log the raw server response at DEBUG level only.
  4. Ensure the MCP tool wrapper follows the same pattern as other tools and returns static error messages.
- **Classification**: **Related** — should be addressed as part of P1-001.

#### M03: Auto-Append Folder Override Could Target Wrong Folder (CVSS 5.0)

- **Vulnerability**: P1-001 allows an optional folder override for auto-append. If the override is accepted from the same untrusted MCP client as the email content, an attacker can redirect sent-mail copies to arbitrary folders (e.g., Trash, a hidden subfolder) without the user's awareness.
- **OWASP A01 (Broken Access Control)**
- **Impact**: Sent messages may be hidden, misrouted, or deleted; loss of mail history; potential evidence tampering.
- **Remediation**:
  1. Treat the folder override as a user-controlled parameter and apply the same `validate_folder_name()` checks used for `create_folder`.
  2. Default the auto-append destination to the folder with the `\Sent` special-use flag detected via `list_folders()`.
  3. If `\Sent` detection fails, require explicit user confirmation before falling back to a name like `Sent`.
  4. Audit log the resolved destination folder for every auto-append operation.
- **Classification**: **Related** — should be addressed as part of P1-001.

#### M04: Message-Id and Threading Header Preservation Risks (CVSS 4.5)

- **Vulnerability**: P1-001 requires preserving `Message-Id`, `References`, and `In-Reply-To` when auto-appending sent messages. If the implementation extracts these from a sent message and re-injects them without re-running `sanitize_message_id()` / `sanitize_references()`, a poisoned value could enter the stored copy. Conversely, re-sanitizing may alter a valid Message-Id if the original was generated by the SMTP client and is already safe.
- **OWASP A05 (Injection)** / A08
- **Impact**: Thread corruption or header injection in the Sent copy; replies may reference the wrong message.
- **Remediation**:
  1. Always generate the Message-Id inside `SMTPClient.send_email()` using a deterministic, sanitized format (e.g., `<{uuid}@{domain}>`) before sending.
  2. Store the same `EmailMessage` object used for SMTP submission, so headers are already sanitized.
  3. When exposing `append_email` with caller-supplied content, re-validate all threading headers with existing helpers.
  4. Add tests that prove the preserved Message-Id in the Sent copy matches the one used during SMTP transmission.
- **Classification**: **Related** — should be addressed as part of P1-001.

#### M05: Auto-Append Failure Must Not Leak Server Details (CVSS 4.0)

- **Vulnerability**: Acceptance criterion 6 states "Send succeeds even if append fails; append failure becomes a warning." If the warning includes the raw IMAP exception or server text, information may leak to the MCP client.
- **OWASP A04 / A10 (Exception Handling Failures)**
- **Impact**: Same as M02; additionally, a partially failed operation may confuse callers that only see a warning.
- **Remediation**:
  1. Return a structured result from `send_email`/`reply_email` such as `{"status": "sent", ..., "append_status": "appended", "append_warning": None}` or `"append_status": "failed", "append_warning": "Copy could not be saved to Sent folder"`.
  2. Do not include exception messages, tracebacks, or server text in the warning.
  3. Log the full failure details at WARNING level in the audit log for operators.
- **Classification**: **Related** — should be addressed as part of P1-001.

---

### Low Findings (CVSS 0.1–3.9)

#### L01: Sent Folder Detection Relies on Server Special-Use Flags (CVSS 2.5)

- **Vulnerability**: P1-001 requires detecting the Sent folder via the `\Sent` special-use flag (RFC 6154). If the server does not advertise special-use flags, the implementation may guess a folder name. A server-side misconfiguration or malicious server could advertise a non-Sent folder with `\Sent`, causing copies to be stored in the wrong place.
- **Impact**: Low in typical deployments; higher if the server is compromised or misconfigured.
- **Remediation**:
  1. Prefer the `\Sent` flag from `list_folders()`.
  2. If no `\Sent` flag exists, fall back to well-known names (`Sent`, `Sent Items`) only after confirming the folder exists.
  3. Allow an explicit override via environment variable or tool argument.
  4. Audit log the detected folder and any fallback decision.
- **Classification**: **New** — backlog hardening item.

#### L02: Re-Append of Identical Message May Create Duplicates (CVSS 2.0)

- **Vulnerability**: APPEND always creates a new message; there is no deduplication. A caller can append the same message repeatedly, or auto-append may run twice if the SMTP send succeeds but the response is retried.
- **Impact**: Duplicate Sent messages; minor clutter and quota use.
- **Remediation**:
  1. Do not retry a successful SMTP send even if the subsequent APPEND fails.
  2. Consider adding a `Message-Id`-based deduplication check in the Sent folder before append, but do not block on it because it is expensive and race-prone.
  3. Document that duplicates are possible with APPEND.
- **Classification**: **New** — backlog item.

---

## Required Input Validation and Sanitization

### Layer 1: MCP Tool `append_email` (`mcp.py`)

Proposed signature:

```python
@dataclass
class AppendFlags:
  """Allowlisted APPEND flags."""
  SEEN = "\\Seen"
  DRAFT = "\\Draft"
  ANSWERED = "\\Answered"
  FLAGGED = "\\Flagged"
  ALL = {SEEN, DRAFT, ANSWERED, FLAGGED}


async def append_email(
  account: Annotated[str, Field(description="Account name")],
  folder: Annotated[str, Field(default="Sent", description="Destination folder")] = "Sent",
  message: Annotated[str, Field(description="RFC 5322 message content")],
  flags: Annotated[list[str] | None, Field(default=None, description="IMAP flags")] = None,
  internal_date: Annotated[str | None, Field(default=None, description="RFC 3501 internal date")] = None,
  ctx: Context | None = None,
) -> dict[str, str]:
```

Validation table:

| Input | Rule | Failure Action |
|-------|------|----------------|
| `account` | Must exist in `get_accounts()` | `ToolError("Account not found: ...")` |
| `folder` | `validate_folder_name(folder)` then `sanitize_folder_name(folder)` | `ToolError` with validation message |
| `message` | Reject empty; enforce max size; reject NUL; re-parse headers and sanitize | `ToolError("Invalid message content")` |
| `flags` | Each flag must be in `AppendFlags.ALL` | `ToolError("Invalid IMAP flag")` |
| `internal_date` | Parse with `email.utils.parsedate_to_datetime`; reject CRLF/ quotes; emit RFC 3501 format | `ToolError("Invalid internal date")` |

### Layer 2: IMAP Client `append_message()` (`imap/client.py`)

```python
async def append_message(
  self,
  folder: str,
  message_bytes: bytes,
  flags: list[str] | None = None,
  internal_date: datetime | None = None,
) -> bool:
```

Validation table:

| Input | Rule | Failure Action |
|-------|------|----------------|
| `folder` | `sanitize_folder_name(validate_folder_name(folder))` | `ValueError` |
| `message_bytes` | Reject `b"\x00"`; enforce max size | `ValueError` |
| `flags` | Re-validate against allowlist | `ValueError` |
| `internal_date` | Accept only timezone-aware `datetime` or `None` | `ValueError` |

### Layer 3: Auto-Append in SMTP Client (`smtp/client.py`)

- Add optional `save_to_sent: bool = False` and `sent_folder: str | None = None` parameters to `send_email()` and `reply_email()`.
- Generate `Message-Id` deterministically before calling `_send()`.
- After successful SMTP send, serialize the same `EmailMessage`/`MIMEMultipart` object to bytes and call `IMAPClient.append_message(folder, message_bytes, flags=["\Seen"])`.
- Catch all append exceptions, log a WARNING with `log_email_appended(..., auto_append=True, success=False, error=generic)`, and include a safe warning in the returned dict.
- Do **not** re-validate or re-sanitize headers that were already produced by the SMTP client.

---

## Audit Logging Requirements

1. Add `log_email_appended()` to `safety/audit.py`:

```python
def log_email_appended(
  account: str,
  folder: str,
  subject_prefix: str,
  message_size: int,
  auto_append: bool = False,
  success: bool = True,
  error: str | None = None,
) -> None:
  log_event(
    event="EMAIL_APPENDED",
    account=account,
    details={
      "folder": folder,
      "subject_prefix": subject_prefix[:50],
      "message_size": message_size,
      "auto_append": auto_append,
      "success": success,
      "error": error,
    },
    level=logging.INFO if success else logging.WARNING,
  )
```

2. Call on:
   - `IMAPClient.append_message()` success.
   - MCP `append_email` tool success.
   - `SMTPClient.send_email()` / `reply_email()` auto-append success and failure.

3. Do not log full message bodies, full recipient lists, or raw IMAP server responses.

---

## Graceful Failure and Error Message Hygiene

1. **Send-then-append semantics**: SMTP send is the primary operation; APPEND is best-effort. If APPEND fails, the send result must still report success.
2. **Structured warning**: Return a dict key `append_warning` that is either `None` or a static, user-safe string such as `"Could not save copy to Sent folder"`.
3. **No raw exceptions**: Never forward `aioimaplib.Error`, `OSError`, or library tracebacks to the MCP client.
4. **No server text**: Map IMAP response codes to generic messages as described in M02.
5. **Continue on lock/timeout**: If the IMAP client is busy or the append times out, log and warn rather than raising a fatal error to the caller.

---

## Test Security Scenarios to Cover

### Unit Tests for `safety/sanitize.py`

1. `validate_folder_name()` rejects CRLF, quotes, backslashes, traversal, and deep nesting for append target folders (same as `create_folder`).
2. A new helper for APPEND flags rejects any flag outside the allowlist.
3. A new helper for `internal_date` rejects CRLF and malformed strings.

### Unit Tests for `imap/client.py`

1. `append_message()` rejects invalid folder names before issuing APPEND.
2. `append_message()` rejects flags outside the allowlist.
3. `append_message()` rejects messages containing NUL bytes.
4. `append_message()` rejects or caps oversized messages.
5. `append_message()` uses `_operation_lock` to serialize APPEND with other IMAP operations.
6. Server `[OVERQUOTA]` is mapped to a generic RuntimeError without leaking server text.
7. Server `[NOPERM]` is mapped to a generic permission error.
8. Successful append calls `log_email_appended()` with correct parameters.

### Unit Tests for `smtp/client.py`

1. `send_email(save_to_sent=True)` calls `IMAPClient.append_message()` with the same message bytes used for SMTP.
2. `send_email(save_to_sent=True)` still returns success when append fails.
3. `send_email(save_to_sent=True)` includes `append_warning` when append fails.
4. `reply_email(save_to_sent=True)` preserves `In-Reply-To` and `References` in the appended copy.
5. `send_email()` and `reply_email()` call `log_email_appended()` on success and on failure.

### MCP Tool Tests (`tests/test_mcp.py`)

1. `append_email` tool rejects non-existent accounts with `ToolError("Account not found")`.
2. `append_email` tool rejects invalid folder names with `ToolError`.
3. `append_email` tool rejects invalid flags.
4. `append_email` tool rejects CRLF in message headers.
5. `append_email` tool rejects oversized messages.
6. `append_email` tool returns `{"status": "appended", "folder": ...}` on success.
7. `send_email` tool with `save_to_sent=True` returns success even if mocked append fails, and includes a warning.
8. `reply_email` tool with `save_to_sent=True` preserves threading headers and returns success on append failure.
9. Rate limiting returns `ToolError("Rate limit exceeded")` for APPEND calls.

### Sync Client Tests

1. `SyncIMAPClient.append_message()` delegates correctly.
2. `SyncSMTPClient.send_email(save_to_sent=True)` delegates correctly and does not hang when append fails.

---

## Security Findings Classification

| Finding | Classification | Action |
|---------|---------------|--------|
| H01: CRLF injection in IMAP APPEND framing | Blocking | Fix in P1-001 |
| H02: Untrusted raw MIME content header injection | Blocking | Fix in P1-001 |
| H03: DoS via large appended messages | Related | Add size cap in P1-001 |
| M01: Missing audit logging for APPEND | Blocking | Add `log_email_appended()` in P1-001 |
| M02: Information disclosure via APPEND errors | Related | Map IMAP codes to generic messages in P1-001 |
| M03: Auto-append folder override risks | Related | Validate override folder and default to `\Sent` in P1-001 |
| M04: Message-Id/header preservation risks | Related | Generate Message-Id before send, reuse same message object in P1-001 |
| M05: Auto-append failure leaks server details | Related | Use structured safe warnings in P1-001 |
| L01: Sent folder detection reliance on flags | New | Add to backlog for hardening |
| L02: Duplicate append risk | New | Add to backlog |

### Blocking/Related Findings Summary

1. **APPEND command injection**: Validate folder, flags, and internal date before any protocol interaction.
2. **MIME header injection**: Re-parse and sanitize caller-supplied message content; for auto-append, reuse the already-sanitized message object.
3. **Message size cap**: Prevent quota/memory exhaustion with a default 25 MB limit.
4. **Audit logging**: Every APPEND operation must be logged.
5. **Error hygiene**: Map IMAP errors to generic user-facing messages and log details internally.
6. **Auto-append safety**: Validate override folders, detect `\Sent`, and ensure send success is independent of append success.

### New Backlog Items

- **H11**: IMAP APPEND-specific rate limit or quota pre-check.
- **H12**: Sent folder special-use flag validation and fallback confirmation.
- **H13**: Duplicate-prevention guard for auto-append based on Message-Id.
