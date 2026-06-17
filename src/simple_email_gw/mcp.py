"""FastMCP server for email operations."""

from __future__ import annotations

import base64
import email
import json
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from simple_email_gw.connections.pool import RateLimitError, get_pool
from simple_email_gw.imap.client import SecurityError
from simple_email_gw.safety.audit import log_event
from simple_email_gw.safety.sanitize import (
  get_append_max_size,
  sanitize_folder_name,
  sanitize_message_id,
  sanitize_references,
  sanitize_subject,
  validate_append_flags,
  validate_folder_name,
)
from simple_email_gw.smtp.client import WhitelistError

# Create FastMCP server
mcp = FastMCP("email")


# --- Tools ---


@mcp.tool
async def list_accounts(ctx: Context | None = None) -> list[dict[str, str]]:
  """List all configured email accounts.

  Returns names and status of each configured account.
  """
  if ctx:
    await ctx.info("Listing configured email accounts")

  try:
    pool = await get_pool()
    accounts = await pool.get_accounts()
    return [{"name": acc.name, "username": acc.username} for acc in accounts]
  except Exception as e:
    raise ToolError("Failed to list accounts. Check server logs for details.") from e


@mcp.tool
async def list_folders(
  account: Annotated[str, Field(description="Account name")],
  ctx: Context | None = None,
) -> list[dict[str, str]]:
  """List all folders/mailboxes for an account.

  Args:
    account: The account name to list folders for.

  Returns:
    List of folder names with their flags and delimiters.
  """
  if ctx:
    await ctx.info(f"Listing folders for account: {account}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    folders = await client.list_folders()
    return folders
  except ValueError:
    raise ToolError(f"Account not found: {account}") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to list folders. Check server logs for details.") from e


@mcp.tool
async def create_folder(
  account: Annotated[str, Field(description="Account name")],
  folder_name: Annotated[
    str,
    Field(description="Name of the folder to create", min_length=1, max_length=255),
  ],
  ctx: Context | None = None,
) -> dict[str, str]:
  """Create a new folder/mailbox on the email account.

  Args:
    account: The account name.
    folder_name: The name of the new folder.

  Returns:
    Dictionary with status and folder name.
  """
  if ctx:
    await ctx.info(f"Creating folder {folder_name} for account: {account}")

  # Defense-in-depth validation at MCP layer
  try:
    folder = validate_folder_name(folder_name)
  except ValueError as e:
    raise ToolError(str(e)) from e

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    await client.create_folder(folder)
    log_event(
      event="FOLDER_CREATED",
      account=account,
      details={"folder": folder},
    )
    return {"status": "created", "folder": folder}
  except ValueError as e:
    msg = str(e)
    if "Account not found" in msg or "not found" in msg.lower():
      raise ToolError(f"Account not found: {account}") from None
    raise ToolError(msg) from e
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except RuntimeError as e:
    raise ToolError(str(e)) from e
  except Exception as e:
    raise ToolError("Failed to create folder. Check server logs for details.") from e


@mcp.tool
async def search_emails(
  account: Annotated[str, Field(description="Account name")],
  folder: Annotated[str, Field(default="INBOX", description="Folder to search")] = "INBOX",
  criteria: Annotated[str, Field(default="ALL", description="IMAP search criteria")] = "ALL",
  limit: Annotated[int, Field(default=50, description="Maximum results", ge=1, le=500)] = 50,
  ctx: Context | None = None,
) -> dict[str, list[str] | int]:
  """Search for emails matching criteria.

  Args:
    account: The account name.
    folder: The folder to search (default: INBOX).
    criteria: IMAP search criteria (default: ALL).
    limit: Maximum number of results (default: 50).

  Returns:
    Dictionary with message_ids and count.
  """
  if ctx:
    await ctx.info(f"Searching emails in {folder} for account: {account}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    ids = await client.search(folder=folder, criteria=criteria, limit=limit)
    return {"message_ids": ids, "count": len(ids)}
  except ValueError:
    raise ToolError(f"Account not found: {account}") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to search emails. Check server logs for details.") from e


@mcp.tool
async def get_email(
  account: Annotated[str, Field(description="Account name")],
  message_id: Annotated[str, Field(description="Message ID to fetch")],
  folder: Annotated[str, Field(default="INBOX", description="Folder name")] = "INBOX",
  ctx: Context | None = None,
) -> dict[str, str | list[str] | bool]:
  """Fetch a single email message by ID.

  Args:
    account: The account name.
    message_id: The message ID to fetch.
    folder: The folder containing the message (default: INBOX).

  Returns:
    Email details including id, folder, subject, from, to, date, body,
    attachments, read (boolean), message_id, and references.
  """
  if ctx:
    await ctx.info(f"Fetching message {message_id} from {folder}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    msg = await client.fetch_message(message_id, folder=folder)
    return msg
  except ValueError:
    raise ToolError(f"Account not found: {account}") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to fetch message. Check server logs for details.") from e


@mcp.tool
async def download_attachment(
  account: Annotated[str, Field(description="Account name")],
  message_id: Annotated[str, Field(description="Message ID")],
  filename: Annotated[str, Field(description="Attachment filename")],
  output_dir: Annotated[str, Field(description="Output directory path")],
  folder: Annotated[str, Field(default="INBOX", description="Folder name")] = "INBOX",
  ctx: Context | None = None,
) -> dict[str, str]:
  """Download an attachment from an email.

  Args:
    account: The account name.
    message_id: The message ID containing the attachment.
    filename: The attachment filename to download.
    output_dir: Directory to save the attachment.
    folder: The folder containing the message (default: INBOX).

  Returns:
    Dictionary with path and filename of the downloaded file.
  """
  if ctx:
    await ctx.info(f"Downloading attachment {filename} from message {message_id}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    path = await client.download_attachment(
      message_id=message_id,
      folder=folder,
      filename=filename,
      output_dir=output_dir,
    )
    return {"path": path, "filename": filename}
  except ValueError as e:
    raise ToolError(str(e)) from e
  except FileNotFoundError:
    raise ToolError(f"Attachment not found: {filename}") from None
  except SecurityError as e:
    raise ToolError(str(e)) from e
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to download attachment. Check server logs for details.") from e


@mcp.tool
async def send_email(
  account: Annotated[str, Field(description="Account name")],
  to: Annotated[list[str], Field(description="Recipient addresses")],
  subject: Annotated[str, Field(description="Email subject")],
  body: Annotated[str, Field(description="Plain text body")],
  cc: Annotated[list[str] | None, Field(default=None, description="CC addresses")] = None,
  bcc: Annotated[list[str] | None, Field(default=None, description="BCC addresses")] = None,
  html_body: Annotated[str | None, Field(default=None, description="HTML body")] = None,
  attachments: Annotated[
    list[str] | None, Field(default=None, description="Attachment paths")
  ] = None,
  append_to_sent: Annotated[
    bool, Field(default=False, description="Append a copy to the Sent folder after sending")
  ] = False,
  append_folder: Annotated[
    str | None, Field(default=None, description="Override destination folder for auto-append")
  ] = None,
  ctx: Context | None = None,
) -> dict[str, Any]:
  """Send a new email message.

  Args:
    account: The account name to send from.
    to: List of recipient email addresses.
    subject: Email subject line.
    body: Plain text body content.
    cc: Optional list of CC addresses.
    bcc: Optional list of BCC addresses.
    html_body: Optional HTML body content.
    attachments: Optional list of file paths to attach.
    append_to_sent: Whether to append a copy to the Sent folder after sending.
    append_folder: Optional override destination folder for auto-append.

  Returns:
    Dictionary with status and recipient information.
  """
  if ctx:
    await ctx.info(f"Sending email to {len(to)} recipient(s) from account: {account}")

  try:
    pool = await get_pool()
    smtp_client = await pool.get_smtp_client(account)
    imap_client = await pool.get_imap_client(account)
    result = await smtp_client.send_email(
      to=to,
      subject=subject,
      body=body,
      cc=cc,
      bcc=bcc,
      html_body=html_body,
      attachments=attachments,
      append_to_sent=append_to_sent,
      append_folder=append_folder,
      imap_client=imap_client,
    )
    return result
  except ValueError as e:
    raise ToolError(str(e)) from e
  except WhitelistError as e:
    raise ToolError(str(e)) from e
  except FileNotFoundError:
    raise ToolError("Attachment file not found") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to send email. Check server logs for details.") from e


@mcp.tool
async def reply_email(
  account: Annotated[str, Field(description="Account name")],
  to: Annotated[str, Field(description="Recipient address")],
  subject: Annotated[str, Field(description="Email subject")],
  body: Annotated[str, Field(description="Plain text body")],
  in_reply_to: Annotated[str, Field(description="Message-ID being replied to")],
  references: Annotated[
    list[str] | None, Field(default=None, description="Thread references")
  ] = None,
  html_body: Annotated[str | None, Field(default=None, description="HTML body")] = None,
  append_to_sent: Annotated[
    bool, Field(default=False, description="Append a copy to the Sent folder after sending")
  ] = False,
  append_folder: Annotated[
    str | None, Field(default=None, description="Override destination folder for auto-append")
  ] = None,
  ctx: Context | None = None,
) -> dict[str, Any]:
  """Reply to an existing email thread.

  Args:
    account: The account name to send from.
    to: The recipient email address.
    subject: Email subject (should include Re: prefix).
    body: Plain text body content.
    in_reply_to: The Message-ID of the email being replied to.
    references: Optional list of Message-IDs in the thread history.
    html_body: Optional HTML body content.
    append_to_sent: Whether to append a copy to the Sent folder after sending.
    append_folder: Optional override destination folder for auto-append.

  Returns:
    Dictionary with status and recipient information.
  """
  if ctx:
    await ctx.info(f"Replying to message: {in_reply_to}")

  try:
    pool = await get_pool()
    smtp_client = await pool.get_smtp_client(account)
    imap_client = await pool.get_imap_client(account)
    result = await smtp_client.reply_email(
      to=to,
      subject=subject,
      body=body,
      in_reply_to=in_reply_to,
      references=references,
      html_body=html_body,
      append_to_sent=append_to_sent,
      append_folder=append_folder,
      imap_client=imap_client,
    )
    return result
  except ValueError as e:
    raise ToolError(str(e)) from e
  except WhitelistError as e:
    raise ToolError(str(e)) from e
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to send reply. Check server logs for details.") from e


@mcp.tool
async def append_email(
  account: Annotated[str, Field(description="Account name")],
  folder: Annotated[str, Field(default="Sent", description="Destination folder")] = "Sent",
  *,
  raw_message: Annotated[str, Field(description="Base64-encoded RFC822 message")],
  flags: Annotated[
    list[str] | None, Field(default=None, description="Optional IMAP flags such as [\\Seen]")
  ] = None,
  ctx: Context | None = None,
) -> dict[str, str]:
  """Append a raw RFC822 message to an IMAP folder.

  Args:
    account: The account name.
    folder: The destination folder (default: Sent).
    raw_message: Base64-encoded RFC822 message content.
    flags: Optional IMAP flags such as [\\Seen].

  Returns:
    Dictionary with status and folder name.
  """
  if ctx:
    await ctx.info(f"Appending message to {folder} for account: {account}")

  # Validate folder name
  try:
    validated_folder = validate_folder_name(folder)
  except ValueError as e:
    raise ToolError(str(e)) from e

  # Validate flags
  try:
    validated_flags = validate_append_flags(flags)
  except ValueError as e:
    raise ToolError(str(e)) from e

  # Decode base64 message content
  try:
    message_bytes = base64.b64decode(raw_message, validate=True)
  except Exception as e:
    raise ToolError("Invalid message content") from e

  if not message_bytes:
    raise ToolError("Invalid message content")
  if b"\x00" in message_bytes:
    raise ToolError("Invalid message content")
  if len(message_bytes) > get_append_max_size():
    raise ToolError("Message exceeds maximum size")

  # Re-parse and sanitize envelope/threading headers
  try:
    msg = email.message_from_bytes(message_bytes)
  except Exception as e:
    raise ToolError("Invalid message content") from e

  for header in ("Subject", "Message-ID", "In-Reply-To", "References"):
    value = msg.get(header)
    if value is not None and ("\r" in value or "\n" in value):
      raise ToolError("Invalid message content")

  try:
    subject = msg.get("Subject")
    if subject:
      msg.replace_header("Subject", sanitize_subject(subject))

    message_id = msg.get("Message-ID")
    if message_id:
      msg.replace_header("Message-ID", sanitize_message_id(message_id))

    in_reply_to = msg.get("In-Reply-To")
    if in_reply_to:
      msg.replace_header("In-Reply-To", sanitize_message_id(in_reply_to))

    references = msg.get("References")
    if references:
      refs = references.split()
      msg.replace_header("References", " ".join(sanitize_references(refs)))
  except ValueError as e:
    raise ToolError("Invalid message content") from e

  # Reject CRLF in address headers
  for header in ("From", "To", "Cc", "Bcc"):
    value = msg.get(header)
    if value and ("\r" in value or "\n" in value):
      raise ToolError("Invalid message content")

  final_bytes = msg.as_bytes()
  safe_folder = sanitize_folder_name(validated_folder)

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    result = await client.append_message(
      folder=safe_folder,
      message_bytes=final_bytes,
      flags=validated_flags,
    )
    return result
  except ValueError as e:
    error_msg = str(e)
    if "Account not found" in error_msg or "not found" in error_msg.lower():
      raise ToolError(f"Account not found: {account}") from None
    raise ToolError(error_msg) from e
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except RuntimeError as e:
    raise ToolError(str(e)) from e
  except Exception as e:
    raise ToolError("Failed to append message. Check server logs for details.") from e


@mcp.tool
async def move_email(
  account: Annotated[str, Field(description="Account name")],
  message_id: Annotated[str, Field(description="Message ID")],
  source_folder: Annotated[str, Field(description="Source folder")],
  dest_folder: Annotated[str, Field(description="Destination folder")],
  ctx: Context | None = None,
) -> dict[str, str]:
  """Move an email between folders.

  Args:
    account: The account name.
    message_id: The message ID to move.
    source_folder: The source folder name.
    dest_folder: The destination folder name.

  Returns:
    Dictionary with status and destination folder.
  """
  if ctx:
    await ctx.info(f"Moving message {message_id} from {source_folder} to {dest_folder}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    await client.move_message(message_id, source_folder, dest_folder)
    return {"status": "moved", "message_id": message_id, "dest_folder": dest_folder}
  except ValueError:
    raise ToolError(f"Account not found: {account}") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to move message. Check server logs for details.") from e


@mcp.tool
async def delete_email(
  account: Annotated[str, Field(description="Account name")],
  message_id: Annotated[str, Field(description="Message ID")],
  folder: Annotated[str, Field(default="INBOX", description="Folder name")] = "INBOX",
  expunge: Annotated[bool, Field(default=True, description="Expunge after delete")] = True,
  ctx: Context | None = None,
) -> dict[str, str]:
  """Delete an email message.

  Args:
    account: The account name.
    message_id: The message ID to delete.
    folder: The folder containing the message (default: INBOX).
    expunge: Whether to expunge after delete (default: True).

  Returns:
    Dictionary with status and message ID.
  """
  if ctx:
    await ctx.info(f"Deleting message {message_id} from {folder}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    await client.delete_message(message_id, folder=folder, expunge=expunge)
    return {"status": "deleted", "message_id": message_id}
  except ValueError:
    raise ToolError(f"Account not found: {account}") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to delete message. Check server logs for details.") from e


@mcp.tool
async def mark_email_read(
  account: Annotated[str, Field(description="Account name")],
  message_id: Annotated[str, Field(description="Message ID")],
  folder: Annotated[str, Field(default="INBOX", description="Folder name")] = "INBOX",
  ctx: Context | None = None,
) -> dict[str, str]:
  """Mark an email message as read.

  Args:
    account: The account name.
    message_id: The message ID to mark as read.
    folder: The folder containing the message (default: INBOX).

  Returns:
    Dictionary with status and message ID.
  """
  if ctx:
    await ctx.info(f"Marking message {message_id} as read in {folder}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    await client.mark_message(message_id, folder, "\\Seen", "add")
    return {"status": "marked_read", "message_id": message_id}
  except ValueError:
    raise ToolError(f"Account not found: {account}") from None
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.") from None
  except Exception as e:
    raise ToolError("Failed to mark message as read. Check server logs for details.") from e


# --- Resources ---


@mcp.resource("email://accounts")
async def list_accounts_resource() -> str:
  """List configured email accounts as a resource."""
  pool = await get_pool()
  accounts = await pool.get_accounts()
  return json.dumps([{"name": acc.name, "username": acc.username} for acc in accounts])


@mcp.resource("email://{account}/folders")
async def list_folders_resource(account: str) -> str:
  """List folders for an account as a resource."""
  pool = await get_pool()
  client = await pool.get_imap_client(account)
  folders = await client.list_folders()
  return json.dumps(folders)


# --- Prompts ---


@mcp.prompt
def compose_email(context: str) -> str:
  """Generate an email composition request.

  Args:
    context: Context for the email (what to write about).

  Returns:
    Prompt for composing an email.
  """
  return f"""Compose a professional email based on the following context:

{context}

Please provide:
1. A clear subject line
2. A professional greeting
3. The main message body
4. An appropriate closing
"""


@mcp.prompt
def summarize_emails(emails: str) -> str:
  """Generate an email summarization request.

  Args:
    emails: List of emails to summarize (as text).

  Returns:
    Prompt for summarizing emails.
  """
  return f"""Summarize the following emails, highlighting:

1. Key topics and themes
2. Action items requiring attention
3. Important dates or deadlines
4. Senders requiring replies

Emails:
{emails}
"""


# --- Main ---


def run() -> None:
  """Run the MCP server."""
  mcp.run()
