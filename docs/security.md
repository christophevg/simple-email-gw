# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Security Features

This package implements multiple security layers to protect against common email-based attacks.

### 1. Transport Security

**TLS 1.2+ Enforcement**

All IMAP and SMTP connections require TLS 1.2 or higher:

```python
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2
```

- Prevents downgrade attacks
- Ensures modern cryptographic standards
- Certificate verification enabled by default

### 2. Header Injection Prevention

**CRLF Injection Protection**

All user-controlled header values are sanitized before use:

- **Subject lines**: CRLF replaced with spaces
- **Message-IDs**: Validated RFC 5322 format
- **References**: Each ID validated individually
- **Email addresses**: CRLF characters rejected

```python
# Sanitization removes/transforms dangerous characters
from simple_email_gw import sanitize_subject

subject = "Hello\r\nBcc: attacker@evil.com"
safe = sanitize_subject(subject)  # "Hello Bcc: attacker@evil.com"
```

### 3. Path Traversal Protection

**Workspace Confinement**

Attachment downloads are confined to a workspace directory:

```python
# Post-write verification
real_path = os.path.realpath(file_path)
Path(real_path).relative_to(real_workspace)  # Raises if escaped
```

- Symlink escape detection (TOCTOU race)
- Path component sanitization
- Hash-based unique filenames

### 4. Rate Limiting

**Token Bucket Algorithm**

Prevents abuse through request rate limits:

- **IMAP**: 60 requests per minute per account
- **SMTP**: 100 sends per hour per account
- Per-account isolation
- Automatic cleanup of expired requests

```python
from simple_email_gw import RateLimiter

limiter = RateLimiter(rate=60, window=60)
if await limiter.acquire("account_name"):
  # Request allowed
  pass
```

### 5. Audit Logging

**Security Event Tracking**

All operations are logged for compliance:

| Event | Log Level |
|-------|-----------|
| Email sent | INFO |
| Authentication success | INFO |
| Authentication failure | WARNING |
| Rate limit exceeded | WARNING |
| Attachment download | INFO |

Logs include:
- Timestamp (UTC)
- Account name
- Operation details
- Limited recipient info (privacy)

### 6. Recipient Whitelist

**Outbound Email Restrictions**

Optional whitelist restricts outgoing emails:

```bash
# Environment configuration
EMAIL_RECIPIENT_DOMAINS=trusted.com,partner.org
EMAIL_RECIPIENT_ADDRESSES=admin@company.com
```

- Domain-based filtering
- Address-based filtering
- Case-insensitive matching

## Known Security Considerations

### IMAP Folder Name Sanitization

**Status**: Fixed (v0.1.0)

Folder names are sanitized with `sanitize_folder_name()` to prevent CRLF injection:
- Rejects folder names containing `\r` or `\n` characters
- Applied to all IMAP folder operations

### SMTP Attachment Filenames

**Status**: Fixed (v0.1.0)

Attachment filenames are sanitized with `sanitize_filename()` to prevent CRLF injection:
- Rejects filenames containing `\r`, `\n`, or `\x00` characters
- Applied before setting Content-Disposition header

### IMAP Message ID Validation

**Status**: Fixed (v0.1.0)

Message IDs are validated with `sanitize_message_id_numeric()`:
- Ensures message IDs are numeric to prevent injection
- Applied to all IMAP message operations

### Rate Limiter Time Source

**Status**: Fixed

The rate limiter uses `time.monotonic()` for timing, preventing clock manipulation attacks.

## Reporting a Vulnerability

**Do not create a public issue for security vulnerabilities.**

Please report security issues to:

- Email: security@christophe.vg
- Include: Description, reproduction steps, potential impact

**Response Timeline**:
- Initial response: Within 48 hours
- Assessment: Within 7 days
- Fix timeline: Depends on severity

## Security Best Practices

### Secret Management

**Environment Variables**

Never commit credentials. Use environment variables:

```bash
# Good: Environment variable
export EMAIL_PASSWORD="app-specific-password"

# Bad: Hardcoded in code
password = "my-password"  # NEVER do this
```

**Connection URIs**

Never log connection strings (they may contain credentials):

```python
# Bad: Logging the entire URI
logger.info(f"Connecting to {uri}")  # May expose password

# Good: Log only hostname
logger.info(f"Connecting to {host}:{port}")
```

### OAuth2 Tokens

For OAuth2 authentication:

```python
account = EmailAccount(
  name="gmail",
  imap_host="imap.gmail.com",
  smtp_host="smtp.gmail.com",
  username="user@gmail.com",
  oauth2_token="ya29.a0...",
  auth_method="oauth2"
)
```

- Tokens should be refreshed regularly
- Store in secure secret management
- Never commit to version control

### Development Security

**Testing**

Run security-focused tests:

```bash
make test  # Includes all security tests
```

**Code Review Checklist**

- [ ] All user inputs sanitized
- [ ] TLS 1.2+ enforced
- [ ] Credentials never logged
- [ ] Rate limits appropriate
- [ ] Whitelist enforced

## References

- [RFC 5322 - Internet Message Format](https://tools.ietf.org/html/rfc5322)
- [RFC 3501 - IMAP4rev1](https://tools.ietf.org/html/rfc3501)
- [RFC 5321 - SMTP](https://tools.ietf.org/html/rfc5321)
- [OWASP - Email Injection](https://owasp.org/www-community/attacks/Email_Injection)
- [CWE-93 - CRLF Injection](https://cwe.mitre.org/data/definitions/93.html)