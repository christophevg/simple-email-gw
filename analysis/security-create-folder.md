# Security Analysis: MCP `create_folder` Tool (MCP-001)

## Security Review Report

### Executive Summary

This security review assesses the proposed `create_folder` MCP tool for the simple-email-gw project. The tool wraps the IMAP CREATE command and introduces unique risks compared to existing read-only or message-manipulation IMAP tools: IMAP command injection via unquoted mailbox names, path traversal through hierarchy separators, denial of service via rapid folder creation, and information disclosure through server error messages. The existing `sanitize_folder_name()` function is insufficient for CREATE because it only blocks CRLF characters, while CREATE requires additional validation for IMAP metacharacters, path traversal patterns, and length limits. This analysis provides a threat model, required input validation rules, error handling recommendations, and a comparison to existing tool security patterns.

---

### Threat Model: `create_folder` MCP Tool

#### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Client / LLM Agent (untrusted input)                  │
│  - account name, folder_name arguments                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Server (mcp.py)                                       │
│  - Pydantic field validation                               │
│  - Error handling, rate limit checks                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  IMAP Client (imap/client.py)                              │
│  - sanitize_folder_name()                                  │
│  - create_folder() method                                  │
│  - Operation-level locking                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Connection Pool (connections/pool.py)                     │
│  - Rate limiting (60 req/min per account)                │
│  - Client lifecycle management                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  IMAP Server (external trust boundary)                     │
│  - Namespace isolation, ACL enforcement                    │
│  - Mailbox storage quota                                   │
└─────────────────────────────────────────────────────────────┘
```

#### STRIDE Threat Analysis

| STRIDE | Threat | Risk | Mitigation Status |
|--------|--------|------|-------------------|
| **Spoofing** | Attacker creates folder with deceptive name mimicking system folders (e.g., `INBOX ` with trailing space, `INB0X` with zero) to confuse users or downstream tools | Medium | **Gap**: No visual similarity or reserved-name checks |
| **Tampering** | IMAP command injection via `folder_name` containing double quotes, backslashes, or CRLF sequences that break protocol framing | **High** | Partial: `sanitize_folder_name()` blocks CRLF only; does not validate IMAP metacharacters |
| **Tampering** | Path traversal via `..` or leading delimiter to create folder outside user namespace (e.g., `../../otheruser/mailbox`) | **High** | **Gap**: No path traversal validation in `sanitize_folder_name()` |
| **Repudiation** | No audit log for folder creation events | Low | **Gap**: `safety/audit.py` lacks `log_folder_created()` |
| **Information Disclosure** | IMAP server error messages reveal internal path structure, usernames, or server software version | Medium | Partial: MCP layer catches generic exceptions but passes `ValueError` through |
| **Information Disclosure** | Folder name itself may contain sensitive PII passed through LLM context | Low | Accepted risk: same as all MCP tools |
| **Denial of Service** | Rapid creation of many folders exhausts server mailbox quota or storage | **High** | Partial: Rate limiter applies, but no per-operation cooldown or folder-count cap |
| **Denial of Service** | Deeply nested folder paths (e.g., `a/b/c/d/...`) exceed server path limits or filesystem depth | Medium | **Gap**: No depth limit validation |
| **Denial of Service** | Extremely long folder names exhaust server buffer limits or storage metadata | Low | **Gap**: No length limit on folder_name |
| **Elevation of Privilege** | Creating folders with reserved names (`INBOX.Draft`, `INBOX.Sent`) may confuse ACL or sync logic on some servers | Low | **Gap**: No reserved-name blacklist |

---

### Critical Findings (CVSS 9.0–10.0)

None identified. The highest risks are High severity due to the layered nature of IMAP server protections (namespaces, ACLs) that typically prevent direct exploitation. However, relying on server-side defenses alone violates defense-in-depth.

---

### High Findings (CVSS 7.0–8.9)

#### H01: IMAP Command Injection via `folder_name` (CVSS 8.1)
- **Vulnerability**: The existing `sanitize_folder_name()` in `safety/sanitize.py` only rejects `\r` and `\n` characters. It does not validate IMAP string metacharacters (`"`, `\`, or null bytes). When passed to `aioimaplib`'s CREATE command, improperly escaped double quotes or backslashes could break IMAP protocol framing, leading to command injection or protocol desynchronization.
- **OWASP A05 (Injection)**
- **Impact**: An attacker could inject arbitrary IMAP commands by crafting a `folder_name` like `Test" NOOP "` or `Test\ NOOP `. While `aioimaplib` may internally quote strings, the library's quoting behavior for CREATE must be verified. If the library uses IMAP quoted strings (RFC 3501), backslash and double-quote characters inside the quoted string must be escaped. If not properly escaped by the library, the attacker controls the protocol stream.
- **Remediation**:
  1. **Validate characters**: Reject `folder_name` containing `"`, `\`, `\x00`, `\r`, `\n`.
  2. **Verify library behavior**: Test `aioimaplib`'s CREATE implementation to confirm it uses IMAP literals or properly escapes quoted strings.
  3. **Defense in depth**: Even if the library escapes correctly, reject these characters at the input layer to prevent future library upgrades from introducing vulnerabilities.
  4. **Use literals if possible**: If the library supports it, prefer IMAP literals (`{length}\r\nstring`) over quoted strings for user-controlled mailbox names.
- **Reference**: [RFC 3501 Section 9 - Formal Syntax](https://datatracker.ietf.org/doc/html/rfc3501#section-9); CWE-89 (Improper Neutralization of Special Elements)
- **Classification**: **Blocking** — must be fixed before `create_folder` is implemented.

#### H02: Path Traversal via Folder Hierarchy (CVSS 7.5)
- **Vulnerability**: IMAP mailbox names can encode hierarchy using server-specific delimiters (e.g., `/` or `.`). A `folder_name` like `../../Public` or `OtherUser/INBOX` could create folders outside the user's intended namespace on servers with weak namespace isolation or shared mailstore backends.
- **OWASP A01 (Broken Access Control) / A05 (Injection)**
- **Impact**: Folder creation outside the personal namespace could lead to data leakage, cross-user contamination, or ACL bypass depending on server configuration. Even on well-configured servers, traversal sequences may create confusing folder structures that break client assumptions.
- **Remediation**:
  1. **Normalize path separators**: Detect the server's hierarchy delimiter via `list_folders()` and validate that `folder_name` does not contain traversal sequences relative to that delimiter.
  2. **Reject `..` segments**: Reject any `folder_name` containing `..` as a path segment (for both `/` and `.` delimiters).
  3. **Reject leading delimiters**: Reject `folder_name` starting with `/` or `.` to prevent absolute-path traversal.
  4. **Enforce namespace prefix**: Prepend the user's personal namespace prefix (e.g., `INBOX/`) if the input does not already include it, so the folder is always created within the user's namespace.
- **Reference**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Classification**: **Blocking** — must be fixed before `create_folder` is implemented.

#### H03: Denial of Service via Rapid Folder Creation (CVSS 7.5)
- **Vulnerability**: The existing IMAP rate limiter allows 60 requests per minute per account. Each `create_folder` call consumes one request. An attacker could create 60 folders per minute, rapidly exhausting server mailbox quotas, filesystem inodes, or IMAP server metadata limits. Unlike read operations, folder creation is a persistent state change that cannot be trivially undone.
- **OWASP A06 (Insecure Design) / A09 (Security Logging Failures)**
- **Impact**: Mailbox quota exhaustion prevents legitimate email delivery. Some IMAP servers degrade performance with many mailboxes. Administrative cleanup may be required.
- **Remediation**:
  1. **Separate rate limiter for state-changing IMAP operations**: Use a stricter rate limit for CREATE (e.g., 10 per minute) distinct from the general IMAP read limit.
  2. **Per-account folder count cap**: Before creating, query `list_folders()` and reject if the account already has more than a configurable maximum (e.g., 500 folders).
  3. **Require explicit confirmation for bulk operations**: If the MCP client invokes multiple creates in sequence, the server should require a session-level confirmation or batch token.
  4. **Audit logging**: Log every folder creation with account name, folder name, and timestamp to support incident response.
- **Reference**: CWE-400 (Uncontrolled Resource Consumption)
- **Classification**: **Related** — should be addressed as part of MCP-001 implementation.

---

### Medium Findings (CVSS 4.0–6.9)

#### M01: Information Disclosure via IMAP Server Error Messages (CVSS 5.3)
- **Vulnerability**: The MCP layer in `mcp.py` catches `Exception` and raises a generic `ToolError("Failed to...")`. However, some IMAP-specific exceptions (e.g., from `aioimaplib.Error`) may propagate through `IMAPClient.create_folder()` with server-provided text like `"No such namespace"` or `"Mailbox already exists: /home/user/mail/test"` that reveal internal paths.
- **OWASP A04 (Cryptographic Failures) — Information Disclosure**
- **Impact**: Internal server paths, usernames, or software versions leaked to the MCP client (and potentially the LLM context) aid reconnaissance for further attacks.
- **Remediation**:
  1. **Catch and mask IMAP errors**: In `IMAPClient.create_folder()`, catch `aioimaplib.Error` and raise `RuntimeError` with a generic message, logging the real server response internally.
  2. **Never pass server text to ToolError**: Ensure the MCP tool wrapper only returns static strings like `"Failed to create folder. Check server logs for details."`
  3. **Log raw responses securely**: Write the full IMAP response to the audit log at `DEBUG` level for troubleshooting.
- **Classification**: **Related** — should be addressed as part of MCP-001 implementation.

#### M02: No Reserved-Name or Namespace Collision Checks (CVSS 5.0)
- **Vulnerability**: Creating folders named `INBOX` (case variants), `INBOX.Drafts`, `INBOX.Sent`, or `INBOX.Trash` may collide with server-assigned special-use mailboxes (RFC 6154). Some servers auto-create these; others fail silently or map them unexpectedly. An attacker could create a folder named `INBOX` in a sub-namespace, confusing clients that rely on case-insensitive or exact matching.
- **OWASP A06 (Insecure Design)**
- **Impact**: Mail client synchronization errors, accidental data loss, or misrouting of emails to attacker-controlled folders.
- **Remediation**:
  1. **Query SPECIAL-USE capabilities**: If the server advertises `SPECIAL-USE` (RFC 6154), block creation of names matching known special-use attributes (`\Drafts`, `\Sent`, `\Trash`, `\Junk`, `\Archive`).
  2. **Block exact `INBOX`**: Reject creation of a folder literally named `INBOX` (case-insensitive) since it is a reserved mailbox name in IMAP.
  3. **Warn on collision**: If `list_folders()` already returns a folder with the same name, return a clear error without attempting CREATE.
- **Classification**: **Related** — should be addressed as part of MCP-001 implementation.

#### M03: Deep Nesting and Name Length DoS (CVSS 4.5)
- **Vulnerability**: IMAP servers typically have limits on mailbox name length (e.g., 255 bytes) and nesting depth. The `create_folder` tool does not validate these limits, so a request with a 500-character name or 50-level deep hierarchy may cause server errors or undefined behavior.
- **OWASP A06 (Insecure Design)**
- **Impact**: Server error responses, potential buffer issues in legacy IMAP daemons, or filesystem-level errors on the mailstore.
- **Remediation**:
  1. **Maximum name length**: Enforce a 255-byte limit on `folder_name` (matching common server limits).
  2. **Maximum nesting depth**: Enforce a maximum of 10 hierarchy levels.
  3. **Validate before sending**: These checks should occur in the MCP tool layer before calling `IMAPClient.create_folder()`.
- **Classification**: **Related** — should be addressed as part of MCP-001 implementation.

#### M04: Missing Audit Log for Folder Creation (CVSS 4.0)
- **Vulnerability**: `safety/audit.py` does not contain a `log_folder_created()` or similar function. Folder creation is a state-changing operation with security relevance, yet it would go unaudited.
- **OWASP A09 (Security Logging Failures)**
- **Impact**: No forensic trail if an attacker creates folders for data staging, exfiltration, or DoS.
- **Remediation**: Add `log_folder_created(account_name: str, folder_name: str)` to `safety/audit.py` and call it from the MCP tool wrapper on success.
- **Classification**: **Related** — should be addressed as part of MCP-001 implementation.

---

### Low Findings (CVSS 0.1–3.9)

#### L01: No UTF-7 Validation for Internationalized Folder Names (CVSS 2.5)
- **Vulnerability**: IMAP uses modified UTF-7 encoding for non-ASCII mailbox names (RFC 3501). Malformed UTF-7 sequences could cause server-side parsing errors or client-side display issues.
- **Impact**: Low direct security impact; primarily a robustness concern. However, some IMAP servers may behave unpredictably with malformed encoding.
- **Remediation**: Validate that `folder_name` is either pure ASCII or valid modified UTF-7. For simplicity, consider restricting `folder_name` to ASCII alphanumeric, space, hyphen, underscore, and delimiter characters.
- **Classification**: **New** — backlog item for hardening.

#### L02: Visual Spoofing via Homoglyphs or Whitespace (CVSS 2.0)
- **Vulnerability**: Folder names with leading/trailing whitespace or Unicode homoglyphs (e.g., `INBOX​` with zero-width space) could deceive users or automated tools into selecting the wrong folder.
- **Impact**: Minor confusion or misrouting if a downstream tool selects the spoofed folder.
- **Remediation**: Strip leading/trailing whitespace and normalize internal whitespace. Consider rejecting non-printable characters.
- **Classification**: **New** — backlog item.

---

## Required Input Validation and Sanitization for `folder_name`

### Layer 1: MCP Tool Layer (`mcp.py`)

Use Pydantic constraints on the `folder_name` field:

```python
folder_name: Annotated[
    str,
    Field(
        description="Name of the folder to create",
        min_length=1,
        max_length=255,
    ),
]
```

Additional manual validations before calling `IMAPClient`:

| Check | Rule | Failure Action |
|-------|------|----------------|
| **Empty check** | `len(folder_name.strip()) == 0` | Raise `ToolError("Folder name cannot be empty")` |
| **Length check** | `len(folder_name.encode("utf-8")) > 255` | Raise `ToolError("Folder name exceeds maximum length")` |
| **CRLF check** | `"\r" in folder_name or "\n" in folder_name` | Raise `ToolError("Folder name contains invalid characters")` |
| **Null byte check** | `"\x00" in folder_name` | Raise `ToolError("Folder name contains invalid characters")` |
| **Quote/backslash check** | `"\"" in folder_name or "\\" in folder_name` | Raise `ToolError("Folder name contains invalid characters")` |
| **Traversal check** | `".." in folder_name.split(delimiter)` or `folder_name.startswith(("/", "."))` | Raise `ToolError("Invalid folder name")` |
| **Depth check** | `len(folder_name.split(delimiter)) > 10` | Raise `ToolError("Folder nesting exceeds maximum depth")` |
| **Reserved name check** | `folder_name.strip().upper() == "INBOX"` | Raise `ToolError("INBOX is a reserved folder name")` |
| **Whitespace normalization** | `folder_name = folder_name.strip()` | Transform silently |

### Layer 2: IMAP Client Layer (`imap/client.py`)

The `create_folder` method should reuse `sanitize_folder_name()` and add CREATE-specific checks:

```python
async def create_folder(self, folder: str) -> bool:
    """Create a new mailbox folder."""
    # Layer 2a: Reuse existing CRLF sanitization
    safe_folder = sanitize_folder_name(folder)

    # Layer 2b: Additional CREATE-specific validation
    # (These are defense-in-depth in case called outside MCP)
    if not safe_folder:
        raise ValueError("Folder name cannot be empty")
    if "\"" in safe_folder or "\\" in safe_folder or "\x00" in safe_folder:
        raise ValueError("Folder name contains invalid characters")
    if ".." in safe_folder.split("/") or ".." in safe_folder.split("."):
        raise ValueError("Invalid folder name")

    async with self._operation_lock:
        client = await self.connect()
        status, _ = await client.create(safe_folder)
        if status != "OK":
            raise RuntimeError("Failed to create folder")
        return True
```

### Notes on Hierarchy Delimiter Detection

The server-specific delimiter (returned by `LIST`) should ideally be detected before validation. However, since `create_folder` is a simple tool, a pragmatic approach is:

1. Treat both `/` and `.` as potential delimiters for traversal checks.
2. Do not allow absolute paths (leading `/` or `.`).
3. Document that the tool creates folders within the user's personal namespace only.

For a stricter implementation:

1. Call `list_folders()` to get the delimiter.
2. Use the detected delimiter for traversal and depth checks.

---

## Error Handling Recommendations

### Error Message Mapping

| IMAP Server Response | Internal Log Message | MCP ToolError Message |
|----------------------|----------------------|-----------------------|
| `NO Mailbox already exists` | Log full response at DEBUG | `"Folder already exists"` |
| `NO Permission denied` | Log full response at WARNING | `"Failed to create folder. Check server logs for details."` |
| `NO Invalid mailbox name` | Log full response at WARNING | `"Invalid folder name. Check server logs for details."` |
| `NO Quota exceeded` | Log full response at WARNING | `"Mailbox quota exceeded. Contact administrator."` |
| Protocol/connection errors | Log exception traceback | `"Failed to create folder. Check server logs for details."` |

### Rules

1. **Never echo `folder_name` back in error messages** if it contains suspicious characters. Return generic messages to prevent reflected injection into logs or LLM context.
2. **Never pass raw IMAP server text to the client.** Always map to a static, vetted error string.
3. **Log server responses securely** to the audit log at `DEBUG` or `WARNING` level for operator troubleshooting.
4. **Raise `ToolError`, not raw exceptions.** The MCP layer must catch all exceptions from `IMAPClient` and wrap them.

---

## Additional Security Controls Needed

### 1. Separate Rate Limiting for Destructive/State-Changing IMAP Operations

The current `imap_limiter` is shared across all IMAP operations (read, search, move, delete). State-changing operations like CREATE should have a stricter limit:

```python
# In safety/rate_limiter.py
imap_write_limiter = RateLimiter(rate=10, window=60)  # 10 creates/deletes per minute
```

The MCP tool should check `imap_write_limiter.acquire(account)` before `get_imap_client()`, or `ConnectionPool` should differentiate read vs write operations.

### 2. Folder Count Cap

Before creation, check the existing folder count:

```python
folders = await client.list_folders()
if len(folders) >= MAX_FOLDERS:
    raise ToolError("Maximum folder limit reached for this account")
```

### 3. Audit Logging

Add to `safety/audit.py`:

```python
def log_folder_created(account_name: str, folder_name: str) -> None:
    """Log a folder creation event."""
    logger.info(
        "folder_created account=%s folder=%s",
        account_name,
        folder_name,
    )
```

Call from `mcp.py` on success.

### 4. Namespace Prefix Enforcement

If the server returns a personal namespace prefix in NAMESPACE (RFC 2342), prepend it to the folder name if missing:

```python
# Pseudocode
if not folder_name.startswith(personal_namespace):
    folder_name = f"{personal_namespace}{delimiter}{folder_name}"
```

This ensures folders are always created within the user's own namespace.

### 5. Post-Creation Verification

After CREATE, verify the folder exists via LIST to detect partial failures or unexpected server behavior:

```python
await client.create_folder(safe_folder)
folders = await client.list_folders()
if not any(f["name"] == safe_folder for f in folders):
    raise RuntimeError("Folder creation could not be verified")
```

---

## Comparison to How Existing Tools Handle Similar Risks

### Existing Tool Security Patterns

| Tool | Folder Input | Sanitization Applied | Rate Limit | Error Handling | Audit Log |
|------|-----------|----------------------|------------|----------------|-----------|
| `list_folders` | None (output only) | N/A | `imap_limiter` | Generic `ToolError` | None |
| `search_emails` | `folder` | `sanitize_folder_name()` + `IMAP_CRITERIA_PATTERN` for criteria | `imap_limiter` | Generic `ToolError` | None |
| `get_email` | `folder` | `sanitize_folder_name()` + `sanitize_message_id_numeric()` | `imap_limiter` | Generic `ToolError` | None |
| `download_attachment` | `folder` | `sanitize_folder_name()` + `sanitize_filename()` + workspace confinement | `imap_limiter` | Generic `ToolError`, `SecurityError` mapped | `log_attachment_download()` |
| `move_email` | `source_folder`, `dest_folder` | `sanitize_folder_name()` for both | `imap_limiter` | Generic `ToolError` | None |
| `delete_email` | `folder` | `sanitize_folder_name()` + `sanitize_message_id_numeric()` | `imap_limiter` | Generic `ToolError` | None |
| `mark_email_read` | `folder` | `sanitize_folder_name()` + `sanitize_message_id_numeric()` | `imap_limiter` | Generic `ToolError` | None |
| `send_email` | N/A (SMTP) | `validate_email()`, `sanitize_subject()`, `sanitize_message_id()`, `sanitize_references()`, `sanitize_filename()` | `smtp_limiter` | Generic `ToolError`, `WhitelistError` mapped | `log_email_sent()` |
| `reply_email` | N/A (SMTP) | Same as `send_email` + `sanitize_message_id()` for threading | `smtp_limiter` | Generic `ToolError`, `WhitelistError` mapped | `log_email_sent()` |

### Key Differences for `create_folder`

1. **More severe injection risk**: While existing tools pass folder names to `SELECT`, `SEARCH`, `FETCH`, `STORE`, `COPY`, `MOVE`, or `EXPUNGE`, those commands either use the folder name in a position with limited injection surface or the operations are read-only. `CREATE` is a write operation that persists state, making injection consequences more durable.

2. **Path traversal is unique to CREATE**: No existing tool creates new hierarchical structures. `move_email` moves messages between existing folders; `create_folder` adds new nodes to the hierarchy, introducing traversal risks.

3. **No audit logging for IMAP state changes**: Existing IMAP tools (move, delete, mark read) do not log to `safety/audit.py`. Only SMTP tools (`send_email`, `reply_email`) and `download_attachment` log. `create_folder` should establish the precedent that state-changing IMAP operations are audited.

4. **Rate limiting should differentiate**: Existing tools all share `imap_limiter` (60 req/min). A malicious sequence of `create_folder` calls could consume this budget and deny service to legitimate read operations. A separate write limiter is recommended.

5. **Reserved name collision**: None of the existing tools introduce new names into the namespace. `create_folder` must validate against reserved names like `INBOX` and special-use mailboxes.

6. **Error message richness**: Existing IMAP tools return generic messages like `"Failed to search emails"`. `create_folder` should maintain this pattern but add specific mappings for common errors (`already exists`, `quota exceeded`) without leaking server internals.

---

## Security Requirements Checklist for MCP-001

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| R01 | Pydantic `max_length=255` on `folder_name` | **Required** | Prevents buffer overflow |
| R02 | Reject empty or whitespace-only `folder_name` | **Required** | Enforce meaningful names |
| R03 | Reject CRLF, null bytes, double quotes, backslashes | **Required** | IMAP command injection prevention |
| R04 | Reject `..` path segments and leading delimiters | **Required** | Path traversal prevention |
| R05 | Enforce maximum nesting depth (10 levels) | **Required** | DoS prevention |
| R06 | Reject `INBOX` (case-insensitive) and special-use names | **Required** | Namespace collision prevention |
| R07 | Use separate rate limiter for write IMAP ops | **Recommended** | DoS prevention |
| R08 | Enforce maximum folder count per account | **Recommended** | Quota protection |
| R09 | Map IMAP server errors to generic client messages | **Required** | Information disclosure prevention |
| R10 | Add `log_folder_created()` audit event | **Recommended** | Forensics |
| R11 | Verify folder creation with `list_folders()` | **Recommended** | Integrity check |
| R12 | Strip leading/trailing whitespace from `folder_name` | **Required** | Consistency |
| R13 | Catch all exceptions in MCP wrapper, return `ToolError` | **Required** | Follow existing pattern |
| R14 | Reuse `sanitize_folder_name()` in `IMAPClient` | **Required** | Consistency with existing tools |
| R15 | Document that tool only creates within personal namespace | **Required** | UX clarity |

---

## Positive Security Observations

1. **Existing `sanitize_folder_name()` provides a baseline** for CRLF injection prevention that `create_folder` can build upon.
2. **Operation-level locking** (`_operation_lock` in `IMAPClient`) prevents race conditions during concurrent folder operations.
3. **Rate limiting infrastructure** already exists and can be extended with minimal effort.
4. **Error handling pattern** in `mcp.py` consistently avoids leaking stack traces or raw server messages to the client.
5. **Pydantic field validation** in MCP tool signatures provides declarative type and bounds checking.

---

## Security Findings Classification

| Finding | Classification | Action |
|---------|---------------|--------|
| IMAP command injection via unescaped quotes/backslashes | **Blocking** | Fix in MCP-001 implementation |
| Path traversal via folder hierarchy | **Blocking** | Fix in MCP-001 implementation |
| Rapid folder creation DoS | **Related** | Add stricter rate limit in MCP-001 |
| Information disclosure via IMAP error messages | **Related** | Add error mapping in MCP-001 |
| Reserved-name / namespace collision | **Related** | Add name checks in MCP-001 |
| Deep nesting / name length DoS | **Related** | Add length/depth limits in MCP-001 |
| Missing audit logging for folder creation | **Related** | Add `log_folder_created()` in MCP-001 |
| No UTF-7 validation | **New** | Add to backlog (LOW priority) |
| Visual spoofing via whitespace/homoglyphs | **New** | Add to backlog (LOW priority) |

---

*Analysis prepared by: Security Engineer*
*Date: 2026-05-16*
*Scope: MCP-001 (`create_folder` tool)*
*Reference Commit: 0b3a3c6*
