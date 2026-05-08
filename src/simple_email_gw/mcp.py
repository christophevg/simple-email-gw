"""FastMCP server for email operations."""

from __future__ import annotations

import json
from typing import Annotated

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from simple_email_gw.connections.pool import RateLimitError, get_pool
from simple_email_gw.imap.client import SecurityError
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
  except Exception:
    raise ToolError("Failed to list accounts. Check server logs for details.")


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
    raise ToolError(f"Account not found: {account}")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to list folders. Check server logs for details.")


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
    raise ToolError(f"Account not found: {account}")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to search emails. Check server logs for details.")


@mcp.tool
async def get_email(
  account: Annotated[str, Field(description="Account name")],
  message_id: Annotated[str, Field(description="Message ID to fetch")],
  folder: Annotated[str, Field(default="INBOX", description="Folder name")] = "INBOX",
  ctx: Context | None = None,
) -> dict[str, str | list[str]]:
  """Fetch a single email message by ID.

  Args:
    account: The account name.
    message_id: The message ID to fetch.
    folder: The folder containing the message (default: INBOX).

  Returns:
    Email details including subject, from, to, date, body, and attachments.
  """
  if ctx:
    await ctx.info(f"Fetching message {message_id} from {folder}")

  try:
    pool = await get_pool()
    client = await pool.get_imap_client(account)
    msg = await client.fetch_message(message_id, folder=folder)
    return msg
  except ValueError:
    raise ToolError(f"Account not found: {account}")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to fetch message. Check server logs for details.")


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
    raise ToolError(str(e))
  except FileNotFoundError:
    raise ToolError(f"Attachment not found: {filename}")
  except SecurityError as e:
    raise ToolError(str(e))
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to download attachment. Check server logs for details.")


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
  ctx: Context | None = None,
) -> dict[str, str]:
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

  Returns:
    Dictionary with status and recipient information.
  """
  if ctx:
    await ctx.info(f"Sending email to {len(to)} recipient(s) from account: {account}")

  try:
    pool = await get_pool()
    client = await pool.get_smtp_client(account)
    result = await client.send_email(
      to=to,
      subject=subject,
      body=body,
      cc=cc,
      bcc=bcc,
      html_body=html_body,
      attachments=attachments,
    )
    return result
  except ValueError as e:
    raise ToolError(str(e))
  except WhitelistError as e:
    raise ToolError(str(e))
  except FileNotFoundError:
    raise ToolError("Attachment file not found")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to send email. Check server logs for details.")


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
  ctx: Context | None = None,
) -> dict[str, str]:
  """Reply to an existing email thread.

  Args:
    account: The account name to send from.
    to: The recipient email address.
    subject: Email subject (should include Re: prefix).
    body: Plain text body content.
    in_reply_to: The Message-ID of the email being replied to.
    references: Optional list of Message-IDs in the thread.
    html_body: Optional HTML body content.

  Returns:
    Dictionary with status and recipient information.
  """
  if ctx:
    await ctx.info(f"Replying to message: {in_reply_to}")

  try:
    pool = await get_pool()
    client = await pool.get_smtp_client(account)
    result = await client.reply_email(
      to=to,
      subject=subject,
      body=body,
      in_reply_to=in_reply_to,
      references=references,
      html_body=html_body,
    )
    return result
  except ValueError as e:
    raise ToolError(str(e))
  except WhitelistError as e:
    raise ToolError(str(e))
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to send reply. Check server logs for details.")


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
    raise ToolError(f"Account not found: {account}")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to move message. Check server logs for details.")


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
    raise ToolError(f"Account not found: {account}")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to delete message. Check server logs for details.")


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
    raise ToolError(f"Account not found: {account}")
  except RateLimitError:
    raise ToolError("Rate limit exceeded. Please try again later.")
  except Exception:
    raise ToolError("Failed to mark message as read. Check server logs for details.")


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
