# MCP Tools Reference

Complete reference for all MCP tools provided by simple-email-gw.

## Account Management

### list_accounts

List all configured email accounts.

**Parameters:** None

**Returns:**
- `name` - Account name
- `username` - Email address/username

**Example:**

```json
[
  {"name": "work", "username": "work@company.com"},
  {"name": "personal", "username": "personal@gmail.com"}
]
```

## Folder Operations

### list_folders

List all folders/mailboxes for an account.

**Parameters:**
- `account` (string, required) - Account name

**Returns:**
- List of folders with flags and delimiter

**Example:**

```json
[
  {"name": "INBOX", "flags": ["\\HasNoChildren"], "delimiter": "/"},
  {"name": "Sent", "flags": ["\\HasNoChildren", "\\Sent"], "delimiter": "/"}
]
```

## Message Operations

### search_emails

Search for messages matching criteria.

**Parameters:**
- `account` (string, required) - Account name
- `folder` (string, default: "INBOX") - Folder to search
- `criteria` (string, default: "ALL") - IMAP search criteria
- `limit` (integer, default: 50) - Maximum results (1-500)

**Returns:**
- `message_ids` - List of message IDs
- `count` - Number of messages found

**Example criteria:**
- `"ALL"` - All messages
- `"UNSEEN"` - Unread messages
- `"FROM sender@example.com"` - From specific sender
- `"SUBJECT keyword"` - Subject contains keyword
- `"SINCE 01-Jan-2024"` - Messages since date

### get_email

Fetch a single message by ID.

**Parameters:**
- `account` (string, required) - Account name
- `message_id` (string, required) - Message ID
- `folder` (string, default: "INBOX") - Folder name

**Returns:**
- `id` - Message ID
- `subject` - Subject line
- `from` - Sender address
- `to` - Recipient addresses
- `date` - Date sent
- `body` - Plain text body
- `attachments` - List of attachment filenames

### send_email

Send a new email message.

**Parameters:**
- `account` (string, required) - Account name
- `to` (array of strings, required) - Recipient addresses
- `subject` (string, required) - Email subject
- `body` (string, required) - Plain text body
- `cc` (array of strings, optional) - CC addresses
- `bcc` (array of strings, optional) - BCC addresses
- `html_body` (string, optional) - HTML body
- `attachments` (array of strings, optional) - Attachment file paths

**Returns:**
- `status` - "sent"
- `recipients` - Number of recipients

### reply_email

Reply to an existing thread.

**Parameters:**
- `account` (string, required) - Account name
- `to` (string, required) - Recipient address
- `subject` (string, required) - Email subject (include Re:)
- `body` (string, required) - Plain text body
- `in_reply_to` (string, required) - Message-ID being replied to
- `references` (array of strings, optional) - Thread references
- `html_body` (string, optional) - HTML body

**Returns:**
- `status` - "sent"
- `recipients` - Number of recipients

### move_email

Move a message between folders.

**Parameters:**
- `account` (string, required) - Account name
- `message_id` (string, required) - Message ID
- `source_folder` (string, required) - Source folder
- `dest_folder` (string, required) - Destination folder

**Returns:**
- `status` - "moved"
- `message_id` - Message ID
- `dest_folder` - Destination folder

### delete_email

Delete a message.

**Parameters:**
- `account` (string, required) - Account name
- `message_id` (string, required) - Message ID
- `folder` (string, default: "INBOX") - Folder name
- `expunge` (boolean, default: true) - Expunge after delete

**Returns:**
- `status` - "deleted"
- `message_id` - Message ID

### mark_email_read

Mark a message as read.

**Parameters:**
- `account` (string, required) - Account name
- `message_id` (string, required) - Message ID
- `folder` (string, default: "INBOX") - Folder name

**Returns:**
- `status` - "marked_read"
- `message_id` - Message ID

## Attachment Operations

### download_attachment

Download an attachment to workspace.

**Parameters:**
- `account` (string, required) - Account name
- `message_id` (string, required) - Message ID
- `filename` (string, required) - Attachment filename
- `output_dir` (string, required) - Output directory path
- `folder` (string, default: "INBOX") - Folder name

**Returns:**
- `path` - Full path to downloaded file
- `filename` - Filename

**Security:**
- Files are saved to workspace directory only
- Path traversal attacks are prevented
- Attachments are verified after write

## Resources

### email://accounts

List configured accounts as a resource.

**Returns:** JSON array of account names and usernames.

### email://{account}/folders

List folders for an account as a resource.

**Parameters:**
- `account` - Account name in URL

**Returns:** JSON array of folder information.

## Prompts

### compose_email

Generate an email composition request.

**Parameters:**
- `context` (string, required) - Context for the email

**Returns:** Prompt for composing an email.

### summarize_emails

Summarize a list of emails.

**Parameters:**
- `emails` (string, required) - List of emails to summarize

**Returns:** Prompt for summarizing emails.

## Error Handling

All tools return errors as `ToolError` with descriptive messages:

- `"Account not found: {account}"` - Invalid account name
- `"Rate limit exceeded. Please try again later."` - Rate limit hit
- `"Attachment not found: {filename}"` - Attachment doesn't exist
- `"Failed to {operation}. Check server logs for details."` - Server error

## Rate Limits

Default rate limits:

| Operation | Limit | Window |
|-----------|-------|--------|
| IMAP | 60 requests | Per minute per account |
| SMTP | 100 sends | Per hour per account |

Rate limits are per-account, so multiple accounts can operate independently.