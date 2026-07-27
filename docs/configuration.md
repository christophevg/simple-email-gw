# Configuration Guide

This document describes all configuration options for simple-email-gw.

## Environment Variables

### Single Account Configuration

For a single email account, use these environment variables:

```bash
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=user@gmail.com
EMAIL_PASSWORD=app-specific-password
EMAIL_ACCOUNT_NAME=default
```

### Multiple Accounts

For multiple accounts, provide a JSON configuration:

```bash
EMAIL_ACCOUNTS_JSON='[
  {
    "name": "work",
    "imap_host": "imap.gmail.com",
    "smtp_host": "smtp.gmail.com",
    "username": "work@example.com",
    "password": "secret"
  },
  {
    "name": "personal",
    "imap_host": "imap.icloud.com",
    "smtp_host": "smtp.icloud.com",
    "username": "personal@icloud.com",
    "password": "secret"
  }
]'
```

### OAuth2 Authentication

For providers that require OAuth2 (like Gmail with modern authentication):

```bash
EMAIL_AUTH_METHOD=oauth2
EMAIL_OAUTH2_TOKEN=ya29.a0...
```

Or in JSON format:

```json
{
  "name": "gmail",
  "imap_host": "imap.gmail.com",
  "smtp_host": "smtp.gmail.com",
  "username": "user@gmail.com",
  "auth_method": "oauth2",
  "oauth2_token": "ya29.a0..."
}
```

## Account Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | "default" | Friendly name for the account |
| `imap_host` | string | required | IMAP server hostname |
| `imap_port` | int | 993 | IMAP server port |
| `smtp_host` | string | required | SMTP server hostname |
| `smtp_port` | int | 587 | SMTP server port |
| `username` | string | required | Email address or username |
| `password` | string | None | Password or app-specific password |
| `oauth2_token` | string | None | OAuth2 access token |
| `auth_method` | string | "password" | Authentication method: "password" or "oauth2" |
| `use_ssl` | bool | True | Use SSL/TLS for connections |

## Rate Limiting

Configure rate limits to prevent abuse:

```bash
EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE=60
EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR=100
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `imap_requests_per_minute` | int | 60 | IMAP requests per minute per account |
| `smtp_sends_per_hour` | int | 100 | SMTP sends per hour per account |

## Recipient Whitelist

Restrict outgoing emails to specific recipients:

### Domain Whitelist

```bash
EMAIL_RECIPIENT_WHITELIST_DOMAINS=gmail.com,icloud.com,company.com
```

### Address Whitelist

```bash
EMAIL_RECIPIENT_WHITELIST_ADDRESSES=admin@company.com,support@partner.org
```

### JSON Configuration

For more complex whitelist configurations:

```bash
EMAIL_RECIPIENT_WHITELIST_JSON='{
  "enabled": true,
  "domains": ["trusted.com", "partner.org"],
  "addresses": ["admin@company.com"]
}'
```

## Workspace Configuration

Attachment downloads are confined to a workspace directory:

```bash
EMAIL_WORKSPACE=/path/to/workspace
```

Default: `/tmp/email_workspace`

## .env File

You can use a `.env` file in the project root for local development:

```bash
# .env
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=user@gmail.com
EMAIL_PASSWORD=app-password
EMAIL_RECIPIENT_WHITELIST_DOMAINS=gmail.com
```

Load the `.env` file automatically:

```python
from simple_email_gw.config import get_config

config = get_config()  # Automatically loads .env if present
```

## Provider-Specific Settings

### Gmail

```bash
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
# Use an app-specific password, not your regular password
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

### iCloud

```bash
EMAIL_IMAP_HOST=imap.mail.me.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.mail.me.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-icloud-email@icloud.com
EMAIL_PASSWORD=app-specific-password
```

### Outlook/Office 365

```bash
EMAIL_IMAP_HOST=outlook.office365.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.office365.com
EMAIL_SMTP_PORT=587
```

## Security Best Practices

1. **Never commit credentials** to version control
2. Use **app-specific passwords** when available
3. Use **OAuth2** for providers that support it
4. Configure **recipient whitelists** to prevent data exfiltration
5. Set appropriate **rate limits** for your use case
6. Use a **dedicated workspace** for attachment downloads