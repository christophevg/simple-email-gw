"""Synchronous wrapper around async SMTPClient using dedicated event loop."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from simple_email_gw.config import EmailAccount
from simple_email_gw.smtp.client import SMTPClient, WhitelistError


class SyncSMTPClient:
  """Synchronous wrapper around SMTPClient using dedicated event loop.

  This wrapper provides a synchronous interface to the async SMTPClient by
  running all async operations in a dedicated event loop on a background thread.

  Attributes:
    _async_client: The wrapped async SMTPClient instance
    _loop: Dedicated event loop running in background thread
    _thread: Background thread running the event loop
  """

  def __init__(self, account: EmailAccount) -> None:
    """Initialize sync wrapper and start background event loop.

    Args:
      account: Email account configuration
    """
    self._async_client = SMTPClient(account)
    self._loop = asyncio.new_event_loop()
    self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
    self._thread.start()

  def __enter__(self) -> SyncSMTPClient:
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
    """Context manager exit - stop event loop and join thread.

    Args:
      exc_type: Exception type if exception occurred
      exc_val: Exception value if exception occurred
      exc_tb: Traceback if exception occurred
    """
    self._loop.call_soon_threadsafe(self._loop.stop)
    self._thread.join(timeout=5.0)

  def _run_coroutine(self, coro: object) -> Any:
    """Run coroutine in dedicated event loop.

    Args:
      coro: Coroutine to execute

    Returns:
      Result from the coroutine

    Raises:
      RuntimeError: If timeout or connection error occurs
      ValueError: If validation error occurs (passed through)
      WhitelistError: If recipient not in whitelist (passed through)
    """
    try:
      future = asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type,var-annotated]
      return future.result()
    except (asyncio.TimeoutError, TimeoutError) as e:
      raise RuntimeError(f"Operation timed out: {e}") from e
    except ConnectionError as e:
      raise RuntimeError(f"Connection error: {e}") from e
    except ValueError:
      # Pass through ValueError (e.g., invalid email)
      raise
    except WhitelistError:
      # Pass through WhitelistError
      raise
    except Exception as e:
      raise RuntimeError(f"Operation failed: {e}") from e

  def send_email(
    self,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    attachments: list[str] | None = None,
  ) -> dict[str, str]:
    """Send an email message.

    Args:
      to: List of recipient email addresses
      subject: Email subject line
      body: Plain text email body
      cc: Optional list of CC recipients
      bcc: Optional list of BCC recipients
      html_body: Optional HTML version of the body
      attachments: Optional list of file paths to attach

    Returns:
      Dict with 'status', 'recipients', and 'message' keys

    Raises:
      RuntimeError: If send fails
      ValueError: If email addresses are invalid
      WhitelistError: If recipients not in whitelist
      FileNotFoundError: If attachment file not found
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.send_email(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html_body=html_body,
        attachments=attachments,
      )
    )

  def reply_email(
    self,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str,
    references: list[str] | None = None,
    html_body: str | None = None,
  ) -> dict[str, str]:
    """Reply to an email message.

    Args:
      to: Recipient email address
      subject: Email subject line
      body: Plain text email body
      in_reply_to: Message-ID being replied to
      references: Optional list of message IDs for References header
      html_body: Optional HTML version of the body

    Returns:
      Dict with 'status', 'recipients', and 'message' keys

    Raises:
      RuntimeError: If send fails
      ValueError: If email addresses are invalid
      WhitelistError: If recipient not in whitelist
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.reply_email(
        to=to,
        subject=subject,
        body=body,
        in_reply_to=in_reply_to,
        references=references,
        html_body=html_body,
      )
    )

  def forward_email(
    self,
    to: list[str],
    subject: str,
    original_from: str,
    original_date: str,
    original_body: str,
  ) -> dict[str, str]:
    """Forward an email message.

    Args:
      to: List of recipient email addresses
      subject: Email subject line
      original_from: Original sender email address
      original_date: Original message date
      original_body: Original message body

    Returns:
      Dict with 'status', 'recipients', and 'message' keys

    Raises:
      RuntimeError: If send fails
      ValueError: If email addresses are invalid
      WhitelistError: If recipients not in whitelist
    """
    return self._run_coroutine(  # type: ignore[no-any-return]
      self._async_client.forward_email(
        to=to,
        subject=subject,
        original_from=original_from,
        original_date=original_date,
        original_body=original_body,
      )
    )
