Sync Client API Reference
=========================

This document describes the synchronous wrapper clients that provide a simpler interface for non-async applications.

Overview
--------

Simple Email Gateway provides both async and sync APIs:

- **Async clients** (IMAPClient, SMTPClient): Recommended for async applications
- **Sync clients** (SyncIMAPClient, SyncSMTPClient): Wrapper clients for simpler synchronous code

Both client types provide identical functionality - sync clients are thin wrappers around async clients using a dedicated event loop in a background thread.

When to Use Sync vs Async
-------------------------

**Use async clients when:**

- Building async applications (FastAPI, Quart, etc.)
- Running in async context (asyncio event loop already running)
- Need maximum performance (no thread overhead)
- Already using async/await throughout your codebase

**Use sync clients when:**

- Building synchronous applications (scripts, CLI tools)
- No existing async context
- Simpler code is more important than performance
- Integrating with legacy synchronous code

Sync Clients Architecture
--------------------------

Sync clients use **Strategy 2**: dedicated event loop in a background thread.

How it works:

1. Each sync client creates its own event loop
2. A daemon thread runs the event loop
3. Methods use ``asyncio.run_coroutine_threadsafe()`` to delegate to async client
4. Context manager ensures proper cleanup (stop loop, join thread)

Benefits:

- Connection pooling works correctly
- No nested event loop issues
- Thread-safe (each client has its own loop/thread)
- Proper cleanup on exceptions

SyncIMAPClient
--------------

.. py:class:: SyncIMAPClient(account: EmailAccount)

   Synchronous wrapper around IMAPClient using dedicated event loop.

   .. py:method:: __init__(account: EmailAccount)

      Initialize sync wrapper and start background event loop.

      :param account: Email account configuration

   .. py:method:: __enter__() -> SyncIMAPClient

      Context manager entry.

      :returns: Self for use in with statements

   .. py:method:: __exit__(exc_type, exc_val, exc_tb) -> None

      Context manager exit - cleanup resources (stop loop, join thread).

   .. py:method:: connect() -> IMAP4_SSL

      Establish IMAP connection.

      :returns: IMAP4_SSL connection object
      :raises RuntimeError: If connection fails

   .. py:method:: disconnect() -> None

      Close IMAP connection and stop background event loop.

   .. py:method:: list_folders() -> list[dict[str, Any]]

      List all folders/mailboxes.

      :returns: List of folder dictionaries with 'name', 'flags', and 'delimiter' keys
      :raises RuntimeError: If operation fails

   .. py:method:: select_folder(folder: str = "INBOX") -> dict[str, int]

      Select a folder and return message count.

      :param folder: Folder name to select (default: "INBOX")
      :returns: Dict with 'folder' and 'count' keys
      :raises RuntimeError: If operation fails

   .. py:method:: search(folder: str = "INBOX", criteria: str = "ALL", limit: int = 50) -> list[str]

      Search for messages matching criteria.

      :param folder: Folder to search (default: "INBOX")
      :param criteria: IMAP search criteria (default: "ALL")
      :param limit: Maximum number of results (default: 50)
      :returns: List of message ID strings
      :raises RuntimeError: If operation fails
      :raises ValueError: If criteria is invalid

   .. py:method:: fetch_message(message_id: str, folder: str = "INBOX") -> dict[str, Any]

      Fetch a single message by ID.

      :param message_id: Message ID to fetch
      :param folder: Folder containing the message (default: "INBOX")
      :returns: Dict with message details (id, folder, subject, from, to, body, attachments)
      :raises RuntimeError: If operation fails
      :raises ValueError: If message_id is invalid

   .. py:method:: move_message(message_id: str, source_folder: str, dest_folder: str) -> bool

      Move a message between folders.

      :param message_id: Message ID to move
      :param source_folder: Source folder name
      :param dest_folder: Destination folder name
      :returns: True if successful
      :raises RuntimeError: If operation fails
      :raises ValueError: If message_id is invalid

   .. py:method:: delete_message(message_id: str, folder: str = "INBOX", expunge: bool = True) -> bool

      Delete a message.

      :param message_id: Message ID to delete
      :param folder: Folder containing the message (default: "INBOX")
      :param expunge: Whether to expunge after deletion (default: True)
      :returns: True if successful
      :raises RuntimeError: If operation fails
      :raises ValueError: If message_id is invalid

   .. py:method:: mark_message(message_id: str, folder: str, flag: str, action: str = "add") -> bool

      Add or remove flags from a message.

      :param message_id: Message ID to mark
      :param folder: Folder containing the message
      :param flag: IMAP flag to add/remove (e.g., "\\Seen")
      :param action: "add" or "remove" (default: "add")
      :returns: True if successful
      :raises RuntimeError: If operation fails
      :raises ValueError: If message_id is invalid

   .. py:method:: download_attachment(message_id: str, folder: str, filename: str, output_dir: str) -> str

      Download an attachment from a message.

      :param message_id: Message ID containing the attachment
      :param folder: Folder containing the message
      :param filename: Attachment filename to download
      :param output_dir: Directory to save the attachment
      :returns: Absolute path to downloaded file
      :raises RuntimeError: If operation fails
      :raises ValueError: If message_id or filename is invalid
      :raises FileNotFoundError: If attachment not found
      :raises SecurityError: If download escapes workspace confinement

   .. py:method:: has_capability(name: str) -> bool

      Check if server supports a capability (synchronous property access).

      :param name: Capability name to check
      :returns: True if capability is supported

SyncSMTPClient
--------------

.. py:class:: SyncSMTPClient(account: EmailAccount)

   Synchronous wrapper around SMTPClient using dedicated event loop.

   .. py:method:: __init__(account: EmailAccount)

      Initialize sync wrapper and start background event loop.

      :param account: Email account configuration

   .. py:method:: __enter__() -> SyncSMTPClient

      Context manager entry.

      :returns: Self for use in with statements

   .. py:method:: __exit__(exc_type, exc_val, exc_tb) -> None

      Context manager exit - stop loop and join thread.

   .. py:method:: send_email(to: list[str], subject: str, body: str, cc: list[str] | None = None, bcc: list[str] | None = None, html_body: str | None = None, attachments: list[str] | None = None) -> dict[str, str]

      Send an email message.

      :param to: List of recipient email addresses
      :param subject: Email subject line
      :param body: Plain text email body
      :param cc: Optional list of CC recipients
      :param bcc: Optional list of BCC recipients
      :param html_body: Optional HTML version of the body
      :param attachments: Optional list of file paths to attach
      :returns: Dict with 'status', 'recipients', and 'message' keys
      :raises RuntimeError: If send fails
      :raises ValueError: If email addresses are invalid
      :raises WhitelistError: If recipients not in whitelist
      :raises FileNotFoundError: If attachment file not found

   .. py:method:: reply_email(to: str, subject: str, body: str, in_reply_to: str, references: list[str] | None = None, html_body: str | None = None) -> dict[str, str]

      Reply to an email message.

      :param to: Recipient email address
      :param subject: Email subject line
      :param body: Plain text email body
      :param in_reply_to: Message-ID being replied to
      :param references: Optional list of message IDs for References header
      :param html_body: Optional HTML version of the body
      :returns: Dict with 'status', 'recipients', and 'message' keys
      :raises RuntimeError: If send fails
      :raises ValueError: If email addresses are invalid
      :raises WhitelistError: If recipient not in whitelist

   .. py:method:: forward_email(to: list[str], subject: str, original_from: str, original_date: str, original_body: str) -> dict[str, str]

      Forward an email message.

      :param to: List of recipient email addresses
      :param subject: Email subject line
      :param original_from: Original sender email address
      :param original_date: Original message date
      :param original_body: Original message body
      :returns: Dict with 'status', 'recipients', and 'message' keys
      :raises RuntimeError: If send fails
      :raises ValueError: If email addresses are invalid
      :raises WhitelistError: If recipients not in whitelist

Usage Examples
--------------

Basic Sync Usage
~~~~~~~~~~~~~~~~

.. code-block:: python

   from simple_email_gw import SyncIMAPClient, SyncSMTPClient, EmailAccount

   # Create account
   account = EmailAccount(
     name="work",
     imap_host="imap.gmail.com",
     smtp_host="smtp.gmail.com",
     username="user@gmail.com",
     password="app-password"
   )

   # Use IMAP client
   with SyncIMAPClient(account) as client:
     folders = client.list_folders()
     messages = client.search(folder="INBOX", criteria="UNSEEN")

     for msg_id in messages:
       msg = client.fetch_message(msg_id)
       print(f"From: {msg['from']}, Subject: {msg['subject']}")

   # Use SMTP client
   with SyncSMTPClient(account) as client:
     result = client.send_email(
       to=["recipient@example.com"],
       subject="Test Email",
       body="Hello from sync client!"
     )
     print(f"Sent: {result}")

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from simple_email_gw import SyncIMAPClient, EmailAccount

   account = EmailAccount(name="work", imap_host="imap.gmail.com", ...)

   with SyncIMAPClient(account) as client:
     try:
       folders = client.list_folders()
     except RuntimeError as e:
       print(f"Connection/operation error: {e}")
     except ValueError as e:
       print(f"Invalid parameter: {e}")

Multiple Operations
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from simple_email_gw import SyncIMAPClient, EmailAccount

   account = EmailAccount(name="work", imap_host="imap.gmail.com", ...)

   with SyncIMAPClient(account) as client:
     # Multiple operations reuse same connection
     folders = client.list_folders()
     client.select_folder("INBOX")
     messages = client.search(criteria="UNSEEN")

     for msg_id in messages:
       msg = client.fetch_message(msg_id)
       # Process message...
       client.mark_message(msg_id, "INBOX", "\\Seen", action="add")

Thread Safety
-------------

Each sync client instance has its own event loop and background thread:

- **Thread-safe**: Multiple clients can run concurrently
- **Isolated**: Each client's event loop is separate
- **No shared state**: No race conditions between instances

.. code-block:: python

   # Safe to use multiple clients concurrently
   client1 = SyncIMAPClient(account1)
   client2 = SyncIMAPClient(account2)

   # Each has its own thread + event loop
   # No interference between clients

Performance Considerations
--------------------------

Sync clients have minimal overhead compared to async clients:

- **Thread overhead**: ~1 MB per client (stack + event loop)
- **Context switching**: Negligible for email operations (network-bound)
- **Connection pooling**: Fully preserved (async client manages pool)

**Best practices:**

- Reuse client instances when possible (context manager pattern)
- Use async clients in high-concurrency async applications
- Sync clients are ideal for scripts, CLI tools, simple applications

Limitations
-----------

**Do NOT use sync clients:**

- Inside async functions (causes nested loop error)
- In async frameworks (FastAPI, Quart, etc.)
- In applications already running event loop

**Error example:**

.. code-block:: python

   # ❌ WRONG: Using sync client in async context
   async def my_async_function():
     with SyncIMAPClient(account) as client:  # Error: nested event loop
       messages = client.search()

   # ✅ CORRECT: Use async client in async context
   async def my_async_function():
     async with IMAPClient(account) as client:
       messages = await client.search()

Migration Guide
----------------

Migrating from async to sync:

.. code-block:: python

   # Before (async)
   async with IMAPClient(account) as client:
     folders = await client.list_folders()
     messages = await client.search(folder="INBOX")

   # After (sync)
   with SyncIMAPClient(account) as client:
     folders = client.list_folders()
     messages = client.search(folder="INBOX")

The only changes needed:

1. Replace ``IMAPClient`` with ``SyncIMAPClient``
2. Replace ``SMTPClient`` with ``SyncSMTPClient``
3. Remove ``async with`` / ``await`` keywords

All methods, parameters, and return values remain identical.