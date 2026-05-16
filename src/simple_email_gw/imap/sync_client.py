"""Synchronous wrapper around async IMAPClient using dedicated event loop."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from aioimaplib import IMAP4_SSL

from simple_email_gw.config import EmailAccount
from simple_email_gw.imap.client import IMAPClient


class SyncIMAPClient:
  """Synchronous wrapper around IMAPClient using dedicated event loop.

  This wrapper provides a synchronous interface to the async IMAPClient by
  running all async operations in a dedicated event loop on a background thread.

  Attributes:
    _async_client: The wrapped async IMAPClient instance
    _loop: Dedicated event loop running in background thread
    _thread: Background thread running the event loop
  """

  def __init__(self, account: EmailAccount) -> None:
    """Initialize sync wrapper and start background event loop.

    Args:
      account: Email account configuration
    """
    self._async_client = IMAPClient(account)
    self._loop = asyncio.new_event_loop()
    self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
    self._thread.start()

  def __enter__(self) -> SyncIMAPClient:
    """Context manager entry.

    Returns:
      Self for use in with statements
    """
    return self

  def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: object,
  ) -> None:
    """Context manager exit - cleanup resources.

    Args:
      exc_type: Exception type if exception occurred
      exc_val: Exception value if exception occurred
      exc_tb: Traceback if exception occurred
    """
    self.disconnect()

  def _run_coroutine(self, coro: object) -> Any:
    """Run coroutine in dedicated event loop.

    Args:
      coro: Coroutine to execute

    Returns:
      Result from the coroutine

    Raises:
      RuntimeError: If timeout or connection error occurs
      ValueError: If validation error occurs (passed through)
    """
    try:
      future = asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type,var-annotated]
      return future.result()
    except (asyncio.TimeoutError, TimeoutError) as e:
      raise RuntimeError(f"Operation timed out: {e}") from e
    except ConnectionError as e:
      raise RuntimeError(f"Connection error: {e}") from e
    except ValueError:
      # Pass through ValueError (e.g., invalid email, invalid message ID)
      raise
    except Exception as e:
      raise RuntimeError(f"Operation failed: {e}") from e

  def connect(self) -> IMAP4_SSL:
    """Establish IMAP connection.

    Returns:
      IMAP4_SSL connection object

    Raises:
      RuntimeError: If connection fails
    """
    return self._run_coroutine(self._async_client.connect())  # type: ignore[no-any-return]

  def disconnect(self) -> None:
    """Close IMAP connection and stop background event loop."""
    try:
      self._run_coroutine(self._async_client.disconnect())
    finally:
      # Always stop the loop and join thread
      self._loop.call_soon_threadsafe(self._loop.stop)
      self._thread.join(timeout=5.0)

  def list_folders(self) -> list[dict[str, Any]]:
    """List all folders/mailboxes.

    Returns:
      List of folder dictionaries with 'name', 'flags', and 'delimiter' keys

    Raises:
      RuntimeError: If operation fails
    """
    return self._run_coroutine(self._async_client.list_folders())  # type: ignore[no-any-return]

  def create_folder(self, folder_name: str) -> bool:
    """Create a new folder/mailbox.

    Args:
      folder_name: Name of the folder to create

    Returns:
      True if successful

    Raises:
      RuntimeError: If operation fails
      ValueError: If folder name contains invalid characters
    """
    return self._run_coroutine(self._async_client.create_folder(folder_name))  # type: ignore[no-any-return]

  def select_folder(self, folder: str = "INBOX") -> dict[str, int]:
    """Select a folder and return message count.

    Args:
      folder: Folder name to select (default: "INBOX")

    Returns:
      Dict with 'folder' and 'count' keys

    Raises:
      RuntimeError: If operation fails
    """
    return self._run_coroutine(self._async_client.select_folder(folder))  # type: ignore[no-any-return]

  def search(
    self,
    folder: str = "INBOX",
    criteria: str = "ALL",
    limit: int = 50,
  ) -> list[str]:
    """Search for messages matching criteria.

    Args:
      folder: Folder to search (default: "INBOX")
      criteria: IMAP search criteria (default: "ALL")
      limit: Maximum number of results (default: 50)

    Returns:
      List of message ID strings

    Raises:
      RuntimeError: If operation fails
      ValueError: If criteria is invalid
    """
    return self._run_coroutine(self._async_client.search(folder, criteria, limit))  # type: ignore[no-any-return]

  def fetch_message(
    self,
    message_id: str,
    folder: str = "INBOX",
  ) -> dict[str, Any]:
    """Fetch a single message by ID.

    Args:
      message_id: Message ID to fetch
      folder: Folder containing the message (default: "INBOX")

    Returns:
      Dict with message details (id, folder, subject, from, to, body, attachments)

    Raises:
      RuntimeError: If operation fails
      ValueError: If message_id is invalid
    """
    return self._run_coroutine(self._async_client.fetch_message(message_id, folder))  # type: ignore[no-any-return]

  def move_message(
    self,
    message_id: str,
    source_folder: str,
    dest_folder: str,
  ) -> bool:
    """Move a message between folders.

    Args:
      message_id: Message ID to move
      source_folder: Source folder name
      dest_folder: Destination folder name

    Returns:
      True if successful

    Raises:
      RuntimeError: If operation fails
      ValueError: If message_id is invalid
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.move_message(message_id, source_folder, dest_folder)
    )

  def delete_message(
    self,
    message_id: str,
    folder: str = "INBOX",
    expunge: bool = True,
  ) -> bool:
    """Delete a message.

    Args:
      message_id: Message ID to delete
      folder: Folder containing the message (default: "INBOX")
      expunge: Whether to expunge after deletion (default: True)

    Returns:
      True if successful

    Raises:
      RuntimeError: If operation fails
      ValueError: If message_id is invalid
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.delete_message(message_id, folder, expunge)
    )

  def mark_message(
    self,
    message_id: str,
    folder: str,
    flag: str,
    action: str = "add",
  ) -> bool:
    """Add or remove flags from a message.

    Args:
      message_id: Message ID to mark
      folder: Folder containing the message
      flag: IMAP flag to add/remove (e.g., "\\Seen")
      action: "add" or "remove" (default: "add")

    Returns:
      True if successful

    Raises:
      RuntimeError: If operation fails
      ValueError: If message_id is invalid
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.mark_message(message_id, folder, flag, action)
    )

  def download_attachment(
    self,
    message_id: str,
    folder: str,
    filename: str,
    output_dir: str,
  ) -> str:
    """Download an attachment from a message.

    Args:
      message_id: Message ID containing the attachment
      folder: Folder containing the message
      filename: Attachment filename to download
      output_dir: Directory to save the attachment

    Returns:
      Absolute path to downloaded file

    Raises:
      RuntimeError: If operation fails
      ValueError: If message_id or filename is invalid
      FileNotFoundError: If attachment not found
      SecurityError: If download escapes workspace confinement
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.download_attachment(message_id, folder, filename, output_dir)
    )

  def has_capability(self, name: str) -> bool:
    """Check if server supports a capability.

    This is a synchronous property check that doesn't require delegation.

    Args:
      name: Capability name to check

    Returns:
      True if capability is supported
    """
    return self._async_client.has_capability(name)
