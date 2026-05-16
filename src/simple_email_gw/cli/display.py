"""
Rich display utilities for CLI output formatting.

This module provides utility functions for formatting and displaying
various types of content using the Rich library, including tables for lists,
panels for individual items, and styled messages for errors and success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from prompt_toolkit import PromptSession
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from simple_email_gw.cli.theme import get_theme_manager
from simple_email_gw.config import get_recipient_whitelist
from simple_email_gw.smtp.client import validate_email, WhitelistError


# Maximum body size in bytes (10 MB)
MAX_BODY_SIZE = 10 * 1024 * 1024


@dataclass
class EmailDraft:
  """Email composition draft state.

  Carries composition state through the multi-step write/reply flow.

  Attributes:
    to: List of primary recipient email addresses
    subject: Email subject line
    body: Email body text
    cc: Optional list of CC recipients
    bcc: Optional list of BCC recipients
    in_reply_to: Message-ID of the original message (for replies)
    references: List of Message-IDs in the thread history
    mode: Composition mode, either "compose" or "reply"
  """

  to: list[str]
  subject: str
  body: str = ""
  cc: list[str] = field(default_factory=list)
  bcc: list[str] = field(default_factory=list)
  in_reply_to: str | None = None
  references: list[str] = field(default_factory=list)
  mode: str = "compose"  # "compose" or "reply"

  def to_preview_dict(self) -> dict[str, str]:
    """Convert draft to preview dictionary for display.

    Returns:
      Dictionary with formatted to, cc, bcc, subject, body fields.
    """
    return {
      "to": ", ".join(self.to) if self.to else "(none)",
      "cc": ", ".join(self.cc) if self.cc else "(none)",
      "bcc": ", ".join(self.bcc) if self.bcc else "(none)",
      "subject": self.subject if self.subject else "(no subject)",
      "body": self.body,
      "mode": self.mode,
    }


def display_accounts(console: Console, accounts: list[dict[str, Any]]) -> None:
  """
  Format and display a table of email accounts.

  Args:
      console: Rich Console instance for output
      accounts: List of account dictionaries with name, username, and status
  """
  theme = get_theme_manager().theme

  if not accounts:
    console.print(Panel("No accounts configured", title="Accounts", style=theme.warning))
    return

  table = Table(title="Accounts")
  table.add_column("Name", style=theme.account_name)
  table.add_column("Username")  # Use default terminal color
  table.add_column("Status")  # Use default terminal color

  for account in accounts:
    name = account.get("name", "")
    username = account.get("username", "")
    status = account.get("status", "available")

    # Format status
    if status == "connected":
      status_text = f"[{theme.success}]connected[/{theme.success}]"
    else:
      status_text = f"[{theme.secondary}]available[/{theme.secondary}]"

    table.add_row(f"[{theme.account_name}]{name}[/{theme.account_name}]", username, status_text)

  console.print(table)


def display_folders(console: Console, folders: list[dict[str, Any]]) -> None:
  """
  Format and display a table of IMAP folders.

  Args:
      console: Rich Console instance for output
      folders: List of folder dictionaries with name, flags, and delimiter
  """
  theme = get_theme_manager().theme

  if not folders:
    console.print(Panel("No folders found", title="Folders", style=theme.warning))
    return

  table = Table(title="Folders")
  table.add_column("Name", style=theme.folder_name)
  table.add_column("Flags")  # Use default terminal color
  table.add_column("Delimiter")  # Use default terminal color

  for folder in folders:
    name = folder.get("name", "")
    flags = folder.get("flags", [])
    delimiter = folder.get("delimiter", "/")

    # Format flags as comma-separated string
    flags_str = ", ".join(flags) if flags else ""

    table.add_row(f"[{theme.folder_name}]{name}[/{theme.folder_name}]", flags_str, delimiter)

  console.print(table)


def display_emails(
  console: Console, messages: list[dict[str, Any]], folder_name: str = "INBOX"
) -> None:
  """
  Format and display a table of email messages.

  Args:
      console: Rich Console instance for output
      messages: List of email dictionaries with id, from, subject, date, and read status
      folder_name: Name of the folder being displayed
  """
  theme = get_theme_manager().theme

  if not messages:
    console.print(
      Panel(
        f"No messages in [bold]{folder_name}[/bold].\n\n"
        f"[{theme.secondary}]Tip: Use 'folders' to see available folders "
        f"or 'cd INBOX' to switch folders.[/{theme.secondary}]",
        title="Emails",
        style=theme.warning,
      )
    )
    return

  table = Table(title="Emails")
  table.add_column("ID", width=6, no_wrap=True, header_style=f"bold {theme.account_name}")
  table.add_column("From", width=28, overflow="ellipsis", header_style=f"bold {theme.account_name}")
  table.add_column(
    "Subject", width=40, overflow="ellipsis", header_style=f"bold {theme.account_name}"
  )
  table.add_column("Date", width=12, no_wrap=True, header_style=f"bold {theme.account_name}")
  table.add_column("Status", width=8, no_wrap=True, header_style=f"bold {theme.account_name}")
  table.caption = f"Folder: {folder_name} | {len(messages)} message(s)"
  table.caption_style = theme.secondary

  for message in messages:
    msg_id = message.get("id", "")
    from_addr = message.get("from", "")
    subject = message.get("subject", "")
    date = message.get("date", "")
    is_read = message.get("read", False)

    # Style based on read status
    if is_read:
      id_text = f"  {msg_id}"
      subject_text = subject
      status_text = f"[{theme.secondary}]read[/{theme.secondary}]"
    else:
      id_text = f"[{theme.unread_indicator}]● {msg_id}[/{theme.unread_indicator}]"
      subject_text = f"[{theme.email_subject_unread}]{subject}[/{theme.email_subject_unread}]"
      status_text = f"[{theme.unread_indicator}]unread[/{theme.unread_indicator}]"

    table.add_row(
      id_text, from_addr, subject_text, f"[{theme.date}]{date}[/{theme.date}]", status_text
    )

  console.print(table)


def display_email(console: Console, email: dict[str, Any]) -> None:
  """
  Format and display a single email message in a panel.

  Args:
      console: Rich Console instance for output
      email: Email dictionary with id, from, to, subject, date, body, and optional attachments
  """
  theme = get_theme_manager().theme

  msg_id = email.get("id", "")
  from_addr = email.get("from", "")
  to_addr = email.get("to", "")
  subject = email.get("subject", "")
  date = email.get("date", "")
  body = email.get("body", "")
  attachments = email.get("attachments", [])

  # Build header string for syntax highlighting
  header = f"From: {from_addr}\nTo: {to_addr}\nSubject: {subject}\nDate: {date}"

  # Create syntax-highlighted header
  syntax = Syntax(header, "email", theme="monokai", line_numbers=False)

  # Create panel for headers
  header_panel = Panel(
    syntax, title=f"[{theme.email_id}]Email #{msg_id}[/{theme.email_id}]", style=theme.secondary
  )

  console.print(header_panel)

  # Display body with pager and markup-safe printing
  with console.pager():
    console.print(Text(body or ""))

  # Display attachments if present
  if attachments:
    console.print("\n[bold]Attachments:[/bold]")
    for attachment in attachments:
      filename = attachment.get("filename", "unknown")
      size = attachment.get("size", 0)
      console.print(f"  • {filename} ({size} bytes)")


def display_error(console: Console, error: str, suggestion: str | None = None) -> None:
  """
  Format and display an error message panel.

  Args:
      console: Rich Console instance for output
      error: Error message to display
      suggestion: Optional suggestion for resolving the error
  """
  theme = get_theme_manager().theme

  # Build error content
  if suggestion:
    content = f"{error}\n\n[{theme.secondary}]Suggestion: {suggestion}[/{theme.secondary}]"
  else:
    content = error

  # Create and display error panel
  panel = Panel(
    content, title=f"[bold {theme.error}]Error[/bold {theme.error}]", style=theme.error_border
  )

  console.print(panel)


def display_success(console: Console, message: str) -> None:
  """
  Format and display a success message panel.

  Args:
      console: Rich Console instance for output
      message: Success message to display
  """
  theme = get_theme_manager().theme

  panel = Panel(
    message,
    title=f"[bold {theme.success}]Success[/bold {theme.success}]",
    style=theme.success_border,
  )

  console.print(panel)


def display_warning(console: Console, message: str) -> None:
  """
  Format and display a warning message panel.

  Args:
      console: Rich Console instance for output
      message: Warning message to display
  """
  theme = get_theme_manager().theme

  panel = Panel(
    message,
    title=f"[bold {theme.warning}]Warning[/bold {theme.warning}]",
    style=theme.warning_border,
  )

  console.print(panel)


async def get_recipients_input(
  console: Console,
  prompt: str,
  session: PromptSession | None = None,
) -> list[str]:
  """Interactive async input for email recipients with validation.

  Validates each recipient email address and checks whitelist restrictions.
  Handles comma-separated input and returns empty list for optional fields.

  Args:
    console: Rich Console instance for output
    prompt: Prompt message for input
    session: Optional PromptSession for async input

  Returns:
    List of validated recipient email addresses

  Raises:
    ValueError: If any email address is invalid
    WhitelistError: If any recipient is blocked by whitelist
  """
  console.print(f"[bold]{prompt}[/bold]")
  console.print("[dim]Enter comma-separated recipient email addresses:[/dim]")

  # Read input line
  try:
    if session is not None:
      user_input = await session.prompt_async("")
    else:
      user_input = input()
  except EOFError:
    return []

  # Parse comma-separated emails
  raw_recipients = [email.strip() for email in user_input.split(",") if email.strip()]

  if not raw_recipients:
    return []

  # Validate each email address
  for addr in raw_recipients:
    validate_email(addr)

  # Check recipient whitelist
  whitelist = get_recipient_whitelist()
  allowed, blocked = whitelist.filter_recipients(raw_recipients)

  if blocked:
    raise WhitelistError(f"Recipients not in whitelist: {', '.join(blocked)}")

  return allowed


async def get_body_input(
  console: Console,
  prompt: str,
  session: PromptSession | None = None,
) -> str:
  """Multi-line body input terminated by Ctrl+D (EOF).

  Collects text line by line until EOFError (Ctrl+D) is received.
  Enforces a maximum body size of 10 MB.

  Args:
    console: Rich Console instance for output
    prompt: Prompt message for input
    session: Optional PromptSession for async input

  Returns:
    Multi-line email body text

  Raises:
    ValueError: If body exceeds the maximum size limit
  """
  console.print(f"[bold]{prompt}[/bold]")
  console.print("[dim]Enter body text. Press Ctrl+D when done.[/dim]")

  lines = []
  total_bytes = 0
  try:
    while True:
      if session is not None:
        line = await session.prompt_async("")
      else:
        line = input()
      lines.append(line)
      total_bytes += len(line.encode("utf-8")) + 1  # +1 for newline
      if total_bytes > MAX_BODY_SIZE:
        raise ValueError(f"Body exceeds maximum size of {MAX_BODY_SIZE / (1024 * 1024):.0f} MB")
  except EOFError:
    # Ctrl+D pressed
    pass
  except KeyboardInterrupt:
    # Ctrl+C - re-raise to allow caller to handle cancellation
    raise

  return "\n".join(lines)


async def confirm_send(
  console: Console,
  draft: EmailDraft,
  session: PromptSession | None = None,
  from_addr: str = "",
) -> bool | None:
  """Display email preview and confirm sending with 3-state return.

  Displays a Rich Table with metadata (From, To, CC, BCC, Subject) and a
  truncated body preview (first 500 characters with continuation note).

  Args:
    console: Rich Console instance for output
    draft: EmailDraft to preview
    session: Optional PromptSession for async input
    from_addr: Sender email address for the From field

  Returns:
    True if user confirms sending, False if user declines, None if user
    chooses to edit the body.
  """
  theme = get_theme_manager().theme

  # Build metadata table
  table = Table(title="Email Preview")
  table.add_column("Field", style=theme.account_name)
  table.add_column("Value")

  preview = draft.to_preview_dict()
  table.add_row("From", from_addr if from_addr else "(unknown)")
  table.add_row("To", preview.get("to", "(none)"))
  table.add_row("CC", preview.get("cc", "(none)"))
  table.add_row("BCC", preview.get("bcc", "(none)"))
  table.add_row("Subject", preview.get("subject", "(no subject)"))

  console.print(table)

  # Truncate body preview to 500 chars
  body_preview = draft.body
  if len(body_preview) > 500:
    remaining = len(body_preview) - 500
    body_preview = body_preview[:500]
    console.print(f"\n{body_preview}")
    console.print(f"[dim]... ({remaining} more characters)[/dim]")
  else:
    console.print(f"\n{body_preview}")

  console.print("\n[bold]Send email? (y/n/e): [/bold]")

  try:
    if session is not None:
      response = await session.prompt_async("")
    else:
      response = input()
    response = response.strip().lower()
    if response in ("y", "yes"):
      return True
    if response in ("n", "no"):
      return False
    if response in ("e", "edit"):
      return None
    # Default to False for unrecognized input
    return False
  except EOFError:
    return False
  except KeyboardInterrupt:
    raise
