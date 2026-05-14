"""
CLI Application Core for interactive email management.

This module provides the EmailCLI class that implements the interactive REPL
(Read-Eval-Print Loop) for managing email operations using the async IMAP/SMTP clients.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.table import Table

from simple_email_gw.cli.display import display_error, display_success
from simple_email_gw.cli.session import Session
from simple_email_gw.cli.theme import ThemeType, get_theme_manager
from simple_email_gw.config import ServerConfig, get_accounts
from simple_email_gw.connections.pool import RateLimitError

if TYPE_CHECKING:
  pass


class EmailCLI:
  """Interactive CLI for managing email operations.

  This class provides a Rich-based terminal interface for email operations
  using the async IMAP/SMTP clients. It implements a REPL loop with command
  parsing, error handling, and session management.

  Attributes:
      console: Rich Console instance for output formatting.
      session: Session manager for account and folder state.
      config: Server configuration loaded from environment.
      prompt_session: PromptSession for async user input.
  """

  def __init__(self) -> None:
    """Initialize the CLI with console, session, config, and prompt session."""
    self.console = Console()
    self.session = Session()
    self.config = ServerConfig()

    # Set up command history file
    history_file = Path.home() / ".email_gw_history"
    history = FileHistory(str(history_file))

    self.prompt_session: PromptSession[str] = PromptSession(history=history)
    self._running = False

  async def run(self) -> None:
    """Run the main REPL loop for the CLI.

    This method:
    1. Displays a welcome message
    2. Enters a loop prompting for user input
    3. Handles commands using handle_command()
    4. Catches and handles exceptions gracefully
    5. Exits on EOFError or quit command

    The method uses patch_stdout for proper async output handling.
    """
    # Display welcome message
    self.console.print("\n[bold cyan]Simple Email Gateway CLI[/bold cyan]")
    self.console.print("[dim]Type 'help' for available commands or 'quit' to exit.[/dim]\n")

    self._running = True

    while self._running:
      try:
        # Get user input with async prompt
        with patch_stdout():
          user_input = await self.prompt_session.prompt_async(self.get_prompt())

        # Handle the command
        await self.handle_command(user_input)

      except KeyboardInterrupt:
        # Ctrl+C - show message and continue
        self.console.print("\n[dim]Press Ctrl+D (or type 'quit') to exit.[/dim]")
        continue

      except EOFError:
        # Ctrl+D - exit gracefully
        self.console.print("\n[dim]Goodbye![/dim]")
        await self._cleanup_and_exit()
        break

      except Exception as e:
        # Catch all other exceptions and display error panel
        self._handle_exception(e)

  async def handle_command(self, input: str) -> None:
    """Parse and execute a user command.

    Args:
        input: The raw user input string.

    This method:
    1. Trims whitespace from input
    2. Handles empty input gracefully
    3. Parses the command and arguments (handling quoted strings)
    4. Routes to the appropriate command handler
    5. Handles unknown commands with error message
    """
    # Trim whitespace
    input = input.strip()

    # Handle empty input
    if not input:
      return

    # Parse command and arguments (case-insensitive for command)
    try:
      # Use shlex to properly handle quoted strings
      parts = shlex.split(input)
    except ValueError as e:
      # Handle shlex parsing errors (e.g., unbalanced quotes)
      display_error(
        self.console, f"Invalid command syntax: {e}", "Use quotes for arguments with spaces"
      )
      return

    if not parts:
      return

    # Extract command (case-insensitive)
    command = parts[0].lower()
    args = parts[1:]

    # Route to command handlers
    try:
      if command == "quit" or command == "exit":
        self._running = False
        self.console.print("[dim]Goodbye![/dim]")
        await self._cleanup_and_exit()

      elif command == "help":
        self.display_help()

      elif command == "status":
        self.display_status()

      elif command == "theme":
        self.toggle_theme()

      elif command == "accounts":
        await self._cmd_accounts()

      elif command == "use":
        await self._cmd_use(args)

      elif command == "folders":
        await self._cmd_folders()

      elif command == "cd":
        await self._cmd_cd(args)

      elif command == "ls":
        await self._cmd_ls(args)

      elif command == "show":
        await self._cmd_show(args)

      elif command == "write":
        await self._cmd_write(args)

      elif command == "reply":
        await self._cmd_reply(args)

      elif command == "delete":
        await self._cmd_delete(args)

      elif command == "move":
        await self._cmd_move(args)

      else:
        display_error(
          self.console,
          f"Unknown command: {command}",
          "Type 'help' for available commands",
        )

    except Exception as e:
      self._handle_exception(e)

  def get_prompt(self) -> HTML:
    """Build the prompt string showing account:folder context.

    Returns:
        A formatted prompt using prompt_toolkit's HTML-like formatting.

    The prompt shows:
    - The current account name (or "none" if no account selected)
    - The current folder name
    - Colors adjusted for current theme (light/dark)
    """

    # Get account name or "none"
    account_name = self.session.current_account.name if self.session.current_account else "none"
    folder_name = self.session.current_folder

    # Get theme colors for prompt
    theme = get_theme_manager().theme

    # Build prompt with theme-aware colors
    return HTML(
      f"<{theme.prompt_account}>{account_name}</{theme.prompt_account}>:<{theme.prompt_folder}>{folder_name}</{theme.prompt_folder}>> "
    )

  async def connect_account(self, name: str) -> None:
    """Connect to a specified email account.

    Args:
        name: The name of the account to connect to.

    Raises:
        ValueError: If account name is not found in configuration.

    This method:
    1. Loads configured accounts
    2. Finds the account by name
    3. Sets it in the session
    4. Sets the current folder to INBOX
    5. Displays success message
    """
    # Get configured accounts
    accounts = get_accounts()

    if not accounts:
      display_error(
        self.console,
        "No email accounts configured",
        "Set EMAIL_ACCOUNTS_JSON or individual EMAIL_* environment variables",
      )
      return

    # Find account by name
    account = None
    for acc in accounts:
      if acc.name == name:
        account = acc
        break

    if account is None:
      # Account not found
      available = ", ".join([acc.name for acc in accounts])
      display_error(self.console, f"Account '{name}' not found", f"Available accounts: {available}")
      return

    # Set account in session
    self.session.set_account(account)

    # Set folder to INBOX
    self.session.set_folder("INBOX")

    # Display success message
    display_success(self.console, f"Connected to account '{account.name}' ({account.username})")

  def display_help(self) -> None:
    """Display help information showing all available commands.

    This method displays a Rich Table with command names, syntax, and descriptions.
    """
    theme = get_theme_manager().theme

    table = Table(title="Available Commands")
    table.add_column("Command", style=theme.account_name)
    table.add_column("Syntax")  # Use default terminal color
    table.add_column("Description", style=theme.secondary)

    # Add commands
    table.add_row("accounts", "accounts", "List all configured email accounts")
    table.add_row("use", "use <account>", "Connect to an email account")
    table.add_row("folders", "folders", "List all folders in current account")
    table.add_row("cd", "cd <folder>", "Change to a different folder")
    table.add_row("ls", "ls [limit]", "List emails in current folder (default: 50)")
    table.add_row("show", "show <message_id>", "Display an email message")
    table.add_row("write", "write <recipient>", "Compose a new email")
    table.add_row("reply", "reply <message_id>", "Reply to an email")
    table.add_row("delete", "delete <message_id>", "Delete an email")
    table.add_row("move", "move <message_id> <folder>", "Move email to a folder")
    table.add_row("status", "status", "Show current session status")
    table.add_row("theme", "theme", "Toggle between light/dark color themes")
    table.add_row("help", "help", "Show this help message")
    table.add_row("quit", "quit", "Exit the CLI")

    self.console.print(table)

  def display_status(self) -> None:
    """Display the current session status including account, folder, and connection state.

    This method shows:
    - Current account name and username (or "None" if no account)
    - Current folder
    - Connection status (Connected/Disconnected)
    - Server information (if connected)
    """
    from rich.panel import Panel

    # Build status lines
    lines = []

    # Account info
    if self.session.current_account:
      lines.append(
        f"[bold]Account:[/bold] {self.session.current_account.name} ({self.session.current_account.username})"
      )
    else:
      lines.append("[bold]Account:[/bold] None")

    # Folder info
    lines.append(f"[bold]Folder:[/bold] {self.session.current_folder}")

    # Connection status
    if self.session._imap_client is not None:
      lines.append("[bold]Connection:[/bold] [green]Connected[/green]")

      # Server info
      if self.session.current_account:
        lines.append(f"[bold]IMAP Server:[/bold] {self.session.current_account.imap_host}")
        lines.append(f"[bold]SMTP Server:[/bold] {self.session.current_account.smtp_host}")
    else:
      lines.append("[bold]Connection:[/bold] [dim]Disconnected[/dim]")

    # Create panel
    panel = Panel("\n".join(lines), title="[bold cyan]Session Status[/bold cyan]", style="white")

    self.console.print(panel)

  def toggle_theme(self) -> None:
    """Toggle between light and dark color themes.

    This method switches between themes optimized for:
    - Light backgrounds (dark text colors for contrast)
    - Dark backgrounds (bright text colors for contrast)
    """
    theme_manager = get_theme_manager()
    new_theme = theme_manager.toggle_theme()

    if new_theme == ThemeType.LIGHT:
      theme_name = "light"
      suggestion = "Best for white/light terminal backgrounds"
    else:
      theme_name = "dark"
      suggestion = "Best for black/dark terminal backgrounds"

    display_success(self.console, f"Switched to {theme_name} theme\n{suggestion}")

  # Placeholder command handlers (to be implemented in later tasks)
  async def _cmd_accounts(self) -> None:
    """List configured accounts."""
    from simple_email_gw.cli.display import display_accounts

    accounts = get_accounts()

    # Convert to dict format for display
    accounts_data = []
    for acc in accounts:
      # Check if this account is currently connected
      if self.session.current_account and self.session.current_account.name == acc.name:
        status = "connected"
      else:
        status = "available"

      accounts_data.append({"name": acc.name, "username": acc.username, "status": status})

    display_accounts(self.console, accounts_data)

  async def _cmd_use(self, args: list[str]) -> None:
    """Connect to specified account."""
    if not args:
      display_error(
        self.console,
        "Usage: use <account_name>",
        "Type 'accounts' to see available accounts",
      )
      return

    account_name = args[0]
    await self.connect_account(account_name)

  async def _cmd_folders(self) -> None:
    """List folders for the current account."""
    from simple_email_gw.cli.display import display_folders

    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    try:
      with self.console.status("Fetching folders..."):
        client = await self.session.get_imap_client()
        folders = await client.list_folders()

      if not folders:
        display_error(
          self.console,
          "No folders found for this account.",
          "Check your account configuration or try another account",
        )
        return

      display_folders(self.console, folders)
    except Exception as e:
      display_error(
        self.console,
        f"Failed to fetch folders: {e}",
        "Check your network connection or credentials",
      )

  async def _cmd_cd(self, args: list[str]) -> None:
    """Change the current folder."""
    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    # Default to INBOX if no folder provided
    target_folder = args[0] if args else "INBOX"

    try:
      client = await self.session.get_imap_client()
      message_count = await client.select_folder(target_folder)

      # Update session state
      self.session.set_folder(target_folder)

      display_success(self.console, f"Changed folder to {target_folder} ({message_count} messages)")
    except RuntimeError:
      # This would typically be "Folder not found" from the client
      display_error(
        self.console,
        f"Folder not found: {target_folder}",
        "Use 'folders' command to see available folders",
      )
    except Exception as e:
      display_error(self.console, f"Error changing folder: {e}", "Try reconnecting to the account")

  async def _cmd_ls(self, args: list[str]) -> None:
    """List emails in the current folder."""
    from simple_email_gw.cli.display import display_emails, display_warning

    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    # Parse and validate limit argument
    try:
      limit = int(args[0]) if args else 50
    except (ValueError, IndexError):
      display_error(
        self.console,
        f"Invalid limit: {args[0] if args else 'empty'}",
        "Usage: ls [limit] where limit is a positive integer",
      )
      return

    if limit < 1:
      display_error(
        self.console,
        f"Invalid limit: {args[0]}",
        "Usage: ls [limit] where limit is a positive integer",
      )
      return

    if limit > 500:
      limit = 500
      display_warning(self.console, "Limit clamped to 500")

    try:
      client = await self.session.get_imap_client()

      # Phase 1: Search for message IDs
      with self.console.status("[bold green]Searching folder...[/bold green]"):
        message_ids = await client.search(
          folder=self.session.current_folder, criteria="ALL", limit=limit
        )

      if not message_ids:
        display_warning(
          self.console,
          f"No messages in {self.session.current_folder}.\n\n"
          f"[dim]Tip: Use 'folders' to see available folders or "
          f"'cd INBOX' to switch folders.[/dim]",
        )
        return

      # Phase 2: Fetch messages sequentially
      messages = []
      try:
        with self.console.status(
          f"[bold green]Fetching {len(message_ids)} messages...[/bold green]"
        ):
          for msg_id in message_ids:
            try:
              msg = await client.fetch_message(msg_id, folder=self.session.current_folder)
              # Ensure read status is present
              msg["read"] = msg.get("read", False)
              self.session.cache_email(msg_id, msg)
              messages.append(msg)
            except Exception:
              # Per-message fetch failure - render placeholder
              placeholder = {
                "id": msg_id,
                "from": "(unknown)",
                "subject": "(fetch failed)",
                "date": "",
                "read": False,
              }
              messages.append(placeholder)
              display_warning(self.console, f"Could not fetch message {msg_id}")
      except KeyboardInterrupt:
        self.console.print("\n[dim]Fetch cancelled.[/dim]")
        return

      display_emails(self.console, messages, folder_name=self.session.current_folder)

    except KeyboardInterrupt:
      self.console.print("\n[dim]Fetch cancelled.[/dim]")
    except (ConnectionError, TimeoutError) as e:
      display_error(self.console, f"Connection failed: {e}", "Check your network and try again")
    except RateLimitError as e:
      display_error(self.console, f"Rate limit exceeded: {e}", "Please wait before trying again")
    except RuntimeError as e:
      display_error(self.console, f"IMAP error: {e}", "Use 'folders' to verify the folder exists")
    except Exception as e:
      display_error(self.console, f"Unexpected error: {e}", "Please try again or check logs")

  async def _cmd_show(self, args: list[str]) -> None:
    """Show email details."""
    from simple_email_gw.cli.display import display_email

    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    if not args:
      display_error(
        self.console,
        "Usage: show <message_id>",
        "Provide a message ID to display",
      )
      return

    message_id = args[0]

    # Validate message ID is numeric
    if not message_id.isdigit():
      display_error(
        self.console,
        "Message ID must be a number. Use 'ls' to see available IDs.",
      )
      return

    # Check cache first
    cached = self.session.get_cached_email(message_id)
    if cached is not None:
      self.console.print("[dim]From cache[/dim]")
      display_email(self.console, cached)
      return

    try:
      client = await self.session.get_imap_client()

      with self.console.status("[bold green]Fetching message...[/bold green]"):
        message = await client.fetch_message(message_id, folder=self.session.current_folder)

      self.session.cache_email(message_id, message)
      display_email(self.console, message)
    except KeyboardInterrupt:
      self.console.print("\n[dim]Fetch cancelled.[/dim]")
    except (ConnectionError, TimeoutError) as e:
      display_error(self.console, f"Connection failed: {e}", "Check your network and try again")
    except RateLimitError as e:
      display_error(self.console, f"Rate limit exceeded: {e}", "Please wait before trying again")
    except RuntimeError as e:
      display_error(self.console, f"IMAP error: {e}", "Check the message ID and try again")
    except Exception as e:
      display_error(self.console, f"Unexpected error: {e}", "Please try again or check logs")

  async def _cmd_write(self, args: list[str]) -> None:
    """Write email (placeholder)."""
    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    display_error(
      self.console,
      "Command not implemented yet",
      "This command will be implemented in a future task",
    )

  async def _cmd_reply(self, args: list[str]) -> None:
    """Reply to email (placeholder)."""
    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    display_error(
      self.console,
      "Command not implemented yet",
      "This command will be implemented in a future task",
    )

  async def _cmd_delete(self, args: list[str]) -> None:
    """Delete email (placeholder)."""
    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    display_error(
      self.console,
      "Command not implemented yet",
      "This command will be implemented in a future task",
    )

  async def _cmd_move(self, args: list[str]) -> None:
    """Move email (placeholder)."""
    if not self.session.current_account:
      display_error(
        self.console,
        "No account selected",
        "Use 'use <account>' to select an account first",
      )
      return

    display_error(
      self.console,
      "Command not implemented yet",
      "This command will be implemented in a future task",
    )

  def _handle_exception(self, e: Exception) -> None:
    """Handle exceptions with appropriate error messages.

    Args:
        e: The exception that was raised.

    This method catches specific exception types and displays
    appropriate error panels with helpful suggestions.
    """
    # Import specific exceptions for handling
    from simple_email_gw.connections.pool import RateLimitError

    if isinstance(e, KeyboardInterrupt):
      # Should not reach here, but handle anyway
      self.console.print("\n[dim]Press Ctrl+D (or type 'quit') to exit.[/dim]")

    elif isinstance(e, EOFError):
      # Should not reach here, but handle anyway
      self.console.print("\n[dim]Goodbye![/dim]")

    elif isinstance(e, ConnectionError):
      display_error(
        self.console,
        f"Connection error: {e}",
        "Check your network connection and server settings",
      )

    elif isinstance(e, RateLimitError):
      display_error(self.console, f"Rate limit exceeded: {e}", "Please wait before trying again")

    elif isinstance(e, ValueError):
      display_error(self.console, f"Validation error: {e}", "Check your input and try again")

    elif isinstance(e, RuntimeError):
      display_error(self.console, f"Operation error: {e}", "Try reconnecting to the account")

    else:
      # Generic error
      display_error(
        self.console,
        f"Unexpected error: {e}",
        "An unexpected error occurred. Please try again.",
      )

  async def _cleanup_and_exit(self) -> None:
    """Cleanup session and exit.

    This method disconnects all active clients before exiting.
    """
    try:
      await self.session.disconnect()
    except Exception:
      # Ignore errors during cleanup
      pass


def main() -> None:
  """Entry point for the CLI application.

  This function:
  1. Loads environment variables from .env file
  2. Creates an EmailCLI instance
  3. Runs the async REPL loop
  4. Handles graceful exit on KeyboardInterrupt or EOFError
  """
  # Redirect audit logs to file to avoid interfering with CLI output
  audit_logger = logging.getLogger("simple_email_gw.audit")
  audit_logger.handlers = []
  log_file = Path.home() / ".email_gw.log"
  file_handler = logging.FileHandler(str(log_file))
  file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
  audit_logger.addHandler(file_handler)

  # Load environment variables from .env file if it exists
  load_dotenv()

  cli = EmailCLI()

  try:
    asyncio.run(cli.run())
  except KeyboardInterrupt:
    # Graceful exit on Ctrl+C
    pass
  except EOFError:
    # Graceful exit on Ctrl+D
    pass
  except SystemExit:
    # Clean exit
    pass
