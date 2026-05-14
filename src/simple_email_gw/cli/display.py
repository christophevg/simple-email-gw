"""
Rich display utilities for CLI output formatting.

This module provides utility functions for formatting and displaying
various types of content using the Rich library, including tables for lists,
panels for individual items, and styled messages for errors and success.
"""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from simple_email_gw.cli.theme import get_theme_manager


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


def get_recipients_input(console: Console, prompt: str) -> list[str]:
  """
  Interactive input for email recipients with validation.

  Args:
      console: Rich Console instance for output
      prompt: Prompt message for input

  Returns:
      List of validated recipient email addresses
  """
  console.print(f"[bold]{prompt}[/bold]")
  console.print("[dim]Enter comma-separated recipient email addresses:[/dim]")

  # Read input line
  try:
    user_input = input()
    # Parse comma-separated emails
    recipients = [email.strip() for email in user_input.split(",") if email.strip()]
    return recipients
  except EOFError:
    return []


def get_body_input(console: Console, prompt: str) -> str:
  """
  Multi-line body input terminated by Ctrl+D (EOF).

  Args:
      console: Rich Console instance for output
      prompt: Prompt message for input

  Returns:
      Multi-line email body text
  """
  console.print(f"[bold]{prompt}[/bold]")
  console.print("[dim]Enter body text. Press Ctrl+D when done.[/dim]")

  lines = []
  try:
    while True:
      line = input()
      lines.append(line)
  except EOFError:
    # Ctrl+D pressed
    pass

  return "\n".join(lines)


def confirm_send(console: Console, preview: dict[str, Any]) -> bool:
  """
  Display email preview and confirm sending.

  Args:
      console: Rich Console instance for output
      preview: Email preview dictionary with to, subject, body fields

  Returns:
      True if user confirms sending, False otherwise
  """
  console.print("\n[bold]Preview:[/bold]")
  console.print(f"  To: {', '.join(preview.get('to', []))}")
  console.print(f"  Subject: {preview.get('subject', '')}")
  console.print(f"  Body:\n{preview.get('body', '')}")
  console.print("\n[bold]Send this email? (y/n)[/bold]")

  try:
    response = input().strip().lower()
    return response == "y" or response == "yes"
  except EOFError:
    return False
