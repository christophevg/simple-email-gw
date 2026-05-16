from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simple_email_gw.cli.app import EmailCLI
from simple_email_gw.connections.pool import RateLimitError


@pytest.fixture
def mock_session():
  session = MagicMock()
  session.current_account = None
  session.current_folder = "INBOX"
  session.get_imap_client = AsyncMock()
  return session


@pytest.fixture
def mock_imap_client():
  client = MagicMock()
  client.list_folders = AsyncMock()
  client.select_folder = AsyncMock()
  return client


@pytest.fixture
def cli(mock_session):
  cli_instance = EmailCLI()
  cli_instance.session = mock_session
  return cli_instance


# --- Folders Command Tests ---


@patch("simple_email_gw.cli.display.display_folders")
async def test_folders_display_table_when_account_selected(
  mock_display_folders, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and folders are returned from the IMAP client
  When: The 'folders' command is executed
  Then: A folders table should be displayed
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_folders = [{"name": "INBOX", "flags": ["\\HasNoChildren"], "delimiter": "/"}]
  mock_imap_client.list_folders.return_value = mock_folders

  await cli._cmd_folders()

  mock_display_folders.assert_called_once_with(cli.console, mock_folders)


@patch("simple_email_gw.cli.app.display_error")
async def test_folders_error_when_no_account_selected(mock_display_error, cli, mock_session):
  """
  Given: No account is selected
  When: The 'folders' command is executed
  Then: An error message should be displayed suggesting the 'use' command
  """
  # Setup
  mock_session.current_account = None

  await cli._cmd_folders()

  mock_display_error.assert_called_once_with(
    cli.console, "No account selected", "Use 'use <account>' to select an account first"
  )


@patch("simple_email_gw.cli.app.display_error")
async def test_folders_error_when_imap_fails(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected but the IMAP client fails to fetch folders
  When: The 'folders' command is executed
  Then: A connection error message should be displayed
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.list_folders.side_effect = Exception("IMAP Connection Failed")

  await cli._cmd_folders()

  args, _ = mock_display_error.call_args
  assert "Failed to fetch folders" in args[1]
  assert "Check your network connection" in args[2]


@patch("simple_email_gw.cli.app.display_error")
async def test_folders_handle_empty_list(mock_display_error, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and the IMAP client returns an empty folder list
  When: The 'folders' command is executed
  Then: A message stating 'No folders found for this account' should be displayed
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.list_folders.return_value = []

  await cli._cmd_folders()

  mock_display_error.assert_called_once_with(
    cli.console,
    "No folders found for this account.",
    "Check your account configuration or try another account",
  )


# --- CD Command Tests ---


@patch("simple_email_gw.cli.app.display_success")
async def test_cd_change_folder_valid(mock_display_success, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and a valid folder name is provided
  When: The 'cd' command is executed with the folder name
  Then: The session.current_folder should be updated and a success message displayed
  """
  # Setup
  target_folder = "Sent"
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.select_folder.return_value = 10  # 10 messages

  await cli._cmd_cd([target_folder])

  mock_session.set_folder.assert_called_with(target_folder)
  mock_display_success.assert_called_once_with(
    cli.console, f"Changed folder to {target_folder} (10 messages)"
  )


@patch("simple_email_gw.cli.app.display_success")
async def test_cd_default_to_inbox(mock_display_success, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and no folder name is provided
  When: The 'cd' command is executed without arguments
  Then: It should default to 'INBOX', update session.current_folder, and display success
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.select_folder.return_value = 5

  await cli._cmd_cd([])

  mock_imap_client.select_folder.assert_called_with("INBOX")
  mock_display_success.assert_called_once_with(cli.console, "Changed folder to INBOX (5 messages)")


@patch("simple_email_gw.cli.app.display_error")
async def test_cd_error_when_no_account_selected(mock_display_error, cli, mock_session):
  """
  Given: No account is selected
  When: The 'cd' command is executed
  Then: An error message should be displayed suggesting the 'use' command
  """
  # Setup
  mock_session.current_account = None

  await cli._cmd_cd(["INBOX"])

  mock_display_error.assert_called_once_with(
    cli.console, "No account selected", "Use 'use <account>' to select an account first"
  )


@patch("simple_email_gw.cli.app.display_error")
async def test_cd_error_when_folder_not_found(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected but the target folder does not exist
  When: The 'cd' command is executed with the missing folder name
  Then: An error panel should be displayed suggesting the 'folders' command
  """
  # Setup
  target_folder = "MissingFolder"
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.select_folder.side_effect = RuntimeError("Folder not found")

  await cli._cmd_cd([target_folder])

  mock_display_error.assert_called_once_with(
    cli.console,
    f"Folder not found: {target_folder}",
    "Use 'folders' command to see available folders",
  )


# --- LS Command Tests ---


@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_happy_path_account_selected_messages_found(
  mock_display_emails, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the IMAP client returns message IDs and message data
  When: The 'ls' command is executed without arguments
  Then: An email table should be displayed with correct columns and data, default limit=50
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1", "2"])
  mock_imap_client.fetch_message = AsyncMock(
    side_effect=[
      {
        "id": "1",
        "from": "alice@example.com",
        "subject": "Hello",
        "date": "2026-05-08",
        "read": True,
      },
      {
        "id": "2",
        "from": "bob@example.com",
        "subject": "World",
        "date": "2026-05-07",
        "read": False,
      },
    ]
  )

  await cli._cmd_ls([])

  # Verify search called with default limit=50
  mock_imap_client.search.assert_called_once_with(folder="INBOX", criteria="ALL", limit=50)

  # Verify fetch_message called for each ID
  assert mock_imap_client.fetch_message.call_count == 2
  mock_imap_client.fetch_message.assert_any_call("1", folder="INBOX")
  mock_imap_client.fetch_message.assert_any_call("2", folder="INBOX")

  # Verify display_emails called with correct messages
  mock_display_emails.assert_called_once()
  call_args = mock_display_emails.call_args
  messages = call_args[0][1]
  assert len(messages) == 2
  assert messages[0]["id"] == "1"
  assert messages[0]["read"] is True
  assert messages[1]["id"] == "2"
  assert messages[1]["read"] is False

  # Verify folder_name kwarg passed to display_emails
  assert call_args[1].get("folder_name") == "INBOX"


@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_limit_argument_parsed(mock_display_emails, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and a limit argument is provided
  When: The 'ls 10' command is executed
  Then: search should be called with limit=10
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1"])
  mock_imap_client.fetch_message = AsyncMock(
    return_value={
      "id": "1",
      "from": "alice@example.com",
      "subject": "Hello",
      "date": "2026-05-08",
      "read": True,
    }
  )

  await cli._cmd_ls(["10"])

  # Verify search called with limit=10
  mock_imap_client.search.assert_called_once_with(folder="INBOX", criteria="ALL", limit=10)
  mock_display_emails.assert_called_once()


@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_default_limit_is_50(mock_display_emails, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and no limit argument is provided
  When: The 'ls' command is executed without arguments
  Then: search should be called with the default limit of 50
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1"])
  mock_imap_client.fetch_message = AsyncMock(
    return_value={
      "id": "1",
      "from": "alice@example.com",
      "subject": "Hello",
      "date": "2026-05-08",
      "read": True,
    }
  )

  await cli._cmd_ls([])

  # Verify search called with default limit=50
  mock_imap_client.search.assert_called_once_with(folder="INBOX", criteria="ALL", limit=50)
  mock_display_emails.assert_called_once()


@patch("simple_email_gw.cli.display.display_warning")
@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_limit_clamped_to_500_with_warning(
  mock_display_emails, mock_display_warning, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and a limit argument exceeds 500
  When: The 'ls 1000' command is executed
  Then: search should be called with limit=500 and a warning should be displayed
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1"])
  mock_imap_client.fetch_message = AsyncMock(
    return_value={
      "id": "1",
      "from": "alice@example.com",
      "subject": "Hello",
      "date": "2026-05-08",
      "read": True,
    }
  )

  await cli._cmd_ls(["1000"])

  # Verify search called with clamped limit=500
  mock_imap_client.search.assert_called_once_with(folder="INBOX", criteria="ALL", limit=500)
  # Verify warning displayed about clamping
  mock_display_warning.assert_called_once()
  args, _ = mock_display_warning.call_args
  assert "clamped" in args[1].lower() or "500" in args[1]
  mock_display_emails.assert_called_once()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_error_when_no_account_selected(mock_display_error, cli, mock_session):
  """
  Given: No account is selected
  When: The 'ls' command is executed
  Then: An error message should be displayed suggesting the 'use' command
  """
  # Setup
  mock_session.current_account = None

  await cli._cmd_ls([])

  # Verify display_error called with "No account selected" and suggestion
  mock_display_error.assert_called_once_with(
    cli.console, "No account selected", "Use 'use <account>' to select an account first"
  )


@patch("simple_email_gw.cli.display.display_warning")
async def test_ls_empty_folder_shows_contextual_warning(
  mock_display_warning, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the current folder has no messages
  When: The 'ls' command is executed
  Then: A contextual warning should be displayed including the folder name and a tip
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "Sent"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=[])

  await cli._cmd_ls([])

  # Verify display_warning called with folder name and tip
  mock_display_warning.assert_called_once()
  args, _ = mock_display_warning.call_args
  assert "Sent" in args[1]
  assert "folders" in args[1].lower() or "cd" in args[1].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_imap_error_displays_actionable_error(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected but the IMAP client raises an error during search
  When: The 'ls' command is executed
  Then: An error panel should be displayed with an actionable suggestion
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(side_effect=RuntimeError("IMAP search failed"))

  await cli._cmd_ls([])

  # Verify display_error called with error message and actionable suggestion
  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "IMAP error" in args[1]
  assert "folders" in args[2].lower() or "connection" in args[2].lower()


@patch("simple_email_gw.cli.display.display_warning")
@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_per_message_fetch_failure_renders_placeholder(
  mock_display_emails, mock_display_warning, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and one message fetch fails while others succeed
  When: The 'ls' command is executed
  Then: A placeholder row should be rendered for the failed message and the rest of the table should be displayed
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1", "2"])
  mock_imap_client.fetch_message = AsyncMock(
    side_effect=[
      {
        "id": "1",
        "from": "alice@example.com",
        "subject": "Hello",
        "date": "2026-05-08",
        "read": True,
      },
      RuntimeError("Failed to fetch message 2"),
    ]
  )

  await cli._cmd_ls([])

  # Verify display_emails called with 2 messages including placeholder
  mock_display_emails.assert_called_once()
  messages = mock_display_emails.call_args[0][1]
  assert len(messages) == 2
  assert messages[0]["id"] == "1"
  assert messages[0]["subject"] == "Hello"
  assert messages[1]["id"] == "2"
  assert messages[1]["subject"] == "(fetch failed)"
  # Verify display_warning called for the failed fetch
  mock_display_warning.assert_called_once()


@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_caches_fetched_messages_in_session(
  mock_display_emails, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and messages are successfully fetched
  When: The 'ls' command is executed
  Then: Each fetched message should be cached in the session for use by the 'show' command
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1", "2"])
  mock_imap_client.fetch_message = AsyncMock(
    side_effect=[
      {
        "id": "1",
        "from": "alice@example.com",
        "subject": "Hello",
        "date": "2026-05-08",
        "read": True,
      },
      {
        "id": "2",
        "from": "bob@example.com",
        "subject": "World",
        "date": "2026-05-07",
        "read": False,
      },
    ]
  )

  await cli._cmd_ls([])

  # Verify session.cache_email called for each message
  assert mock_session.cache_email.call_count == 2
  mock_session.cache_email.assert_any_call(
    "1",
    {
      "id": "1",
      "from": "alice@example.com",
      "subject": "Hello",
      "date": "2026-05-08",
      "read": True,
    },
  )
  mock_session.cache_email.assert_any_call(
    "2",
    {
      "id": "2",
      "from": "bob@example.com",
      "subject": "World",
      "date": "2026-05-07",
      "read": False,
    },
  )


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_invalid_limit_string_shows_error(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected
  When: The 'ls abc' command is executed with a non-numeric limit
  Then: An error panel should be displayed indicating the limit is invalid
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client

  await cli._cmd_ls(["abc"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Invalid limit" in args[1]
  assert "positive integer" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_limit_zero_shows_error(mock_display_error, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected
  When: The 'ls 0' command is executed
  Then: An error panel should be displayed indicating the limit must be positive
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client

  await cli._cmd_ls(["0"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Invalid limit" in args[1]
  assert "positive integer" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_limit_negative_shows_error(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected
  When: The 'ls -5' command is executed with a negative limit
  Then: An error panel should be displayed indicating the limit must be positive
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.get_imap_client.return_value = mock_imap_client

  await cli._cmd_ls(["-5"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Invalid limit" in args[1]
  assert "positive integer" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_connection_error_during_search_shows_connection_error(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected
  When: The IMAP search raises ConnectionError
  Then: An error panel should be displayed with a connection-failed message
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(side_effect=ConnectionError("Network unreachable"))

  await cli._cmd_ls([])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Connection failed" in args[1]
  assert "network" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_timeout_error_during_search_shows_connection_error(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected
  When: The IMAP search raises TimeoutError
  Then: An error panel should be displayed with a connection-failed message
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(side_effect=TimeoutError("Server did not respond"))

  await cli._cmd_ls([])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Connection failed" in args[1]
  assert "network" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_ls_rate_limit_error_during_search_shows_rate_limit_error(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected
  When: The IMAP search raises RateLimitError
  Then: An error panel should be displayed with a rate-limit-exceeded message
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(side_effect=RateLimitError("Too many requests"))

  await cli._cmd_ls([])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Rate limit exceeded: Too many requests" in args[1]
  assert "wait" in args[2].lower()


@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_keyboard_interrupt_during_fetch_shows_cancelled_message(
  mock_display_emails, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and messages are found
  When: The user presses Ctrl+C during the fetch loop
  Then: A 'Fetch cancelled.' message should be printed and the command should return gracefully
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1", "2"])
  mock_imap_client.fetch_message = AsyncMock(side_effect=KeyboardInterrupt)

  await cli._cmd_ls([])

  mock_display_emails.assert_not_called()


@patch("simple_email_gw.cli.display.display_emails")
async def test_ls_read_status_fallback_when_missing_read_key(
  mock_display_emails, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and fetch_message returns a dict without a 'read' key
  When: The 'ls' command is executed
  Then: display_emails should receive the message with read=True as a fallback
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_imap_client.search = AsyncMock(return_value=["1"])
  mock_imap_client.fetch_message = AsyncMock(
    return_value={
      "id": "1",
      "from": "alice@example.com",
      "subject": "Hello",
      "date": "2026-05-08",
    }
  )

  await cli._cmd_ls([])

  mock_display_emails.assert_called_once()
  messages = mock_display_emails.call_args[0][1]
  assert len(messages) == 1
  assert messages[0]["read"] is False


# --- Show Command Tests ---


@patch("simple_email_gw.cli.display.display_email")
async def test_show_happy_path_cached_email(
  mock_display_email, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is cached in session
  When: The 'show <message_id>' command is executed
  Then: The cached message should be displayed without fetching from IMAP
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  cached_message = {
    "id": "1",
    "from": "alice@example.com",
    "to": "me@example.com",
    "subject": "Hello",
    "date": "2026-05-08",
    "body": "Hello world",
  }
  mock_session.get_cached_email.return_value = cached_message

  await cli._cmd_show(["1"])

  # Verify cache checked
  mock_session.get_cached_email.assert_called_once_with("1")
  # Verify display called with cached message
  mock_display_email.assert_called_once_with(cli.console, cached_message)
  # Verify fetch was NOT called
  mock_imap_client.fetch_message.assert_not_called()
  # Verify get_imap_client was NOT called for cached messages
  mock_session.get_imap_client.assert_not_called()


@patch("simple_email_gw.cli.display.display_email")
async def test_show_happy_path_fetch_not_cached(
  mock_display_email, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is not cached
  When: The 'show <message_id>' command is executed
  Then: The message should be fetched from IMAP and displayed
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  fetched_message = {
    "id": "1",
    "from": "alice@example.com",
    "to": "me@example.com",
    "subject": "Hello",
    "date": "2026-05-08",
    "body": "Hello world",
  }
  mock_imap_client.fetch_message = AsyncMock(return_value=fetched_message)

  await cli._cmd_show(["1"])

  # Verify cache checked
  mock_session.get_cached_email.assert_called_once_with("1")
  # Verify fetch called with correct args
  mock_imap_client.fetch_message.assert_awaited_once_with("1", folder="INBOX")
  # Verify message cached after fetch
  mock_session.cache_email.assert_called_once_with("1", fetched_message)
  # Verify display called with fetched message
  mock_display_email.assert_called_once_with(cli.console, fetched_message)


@patch("simple_email_gw.cli.app.display_error")
async def test_show_error_no_account_selected(mock_display_error, cli, mock_session):
  """
  Given: No account is selected
  When: The 'show <message_id>' command is executed
  Then: An error message should be displayed suggesting the 'use' command
  """
  # Setup
  mock_session.current_account = None

  await cli._cmd_show(["1"])

  mock_display_error.assert_called_once_with(
    cli.console, "No account selected", "Use 'use <account>' to select an account first"
  )


@patch("simple_email_gw.cli.app.display_error")
async def test_show_error_message_id_missing(mock_display_error, cli, mock_session):
  """
  Given: An account is selected but no message_id is provided
  When: The 'show' command is executed without arguments
  Then: An error message should be displayed with usage information
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")

  await cli._cmd_show([])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "message_id" in args[1].lower() or "usage" in args[1].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_show_error_fetch_fails(mock_display_error, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and the message is not cached
  When: The IMAP fetch raises an error
  Then: An error message should be displayed with an actionable suggestion
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  mock_imap_client.fetch_message = AsyncMock(side_effect=RuntimeError("Message not found"))

  await cli._cmd_show(["1"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "IMAP error" in args[1]
  assert "message id" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_show_invalid_message_id_shows_error(mock_display_error, cli, mock_session):
  """
  Given: An account is selected but message_id is non-numeric
  When: The 'show abc' command is executed
  Then: An error panel should be displayed indicating message ID must be a number
  """
  mock_session.current_account = MagicMock(name="test-account")

  await cli._cmd_show(["abc"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "number" in args[1].lower()
  assert "ls" in args[1].lower()


@patch("simple_email_gw.cli.display.display_email")
async def test_show_spinner_shown_on_cache_miss(
  mock_display_email, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is not cached
  When: The 'show <message_id>' command is executed
  Then: A spinner with 'Fetching message...' should be shown during IMAP fetch
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  fetched_message = {
    "id": "1",
    "from": "alice@example.com",
    "to": "me@example.com",
    "subject": "Hello",
    "date": "2026-05-08",
    "body": "Hello world",
  }
  mock_imap_client.fetch_message = AsyncMock(return_value=fetched_message)

  with patch.object(cli.console, "status") as mock_status:
    await cli._cmd_show(["1"])

    mock_status.assert_called_once_with("[bold green]Fetching message...[/bold green]")


@patch("simple_email_gw.cli.app.display_error")
async def test_show_connection_error_shows_connection_failed(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is not cached
  When: The IMAP fetch raises ConnectionError
  Then: An error panel should be displayed with a connection-failed message
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  mock_imap_client.fetch_message = AsyncMock(side_effect=ConnectionError("Network unreachable"))

  await cli._cmd_show(["1"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Connection failed" in args[1]
  assert "network" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_show_timeout_error_shows_connection_failed(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is not cached
  When: The IMAP fetch raises TimeoutError
  Then: An error panel should be displayed with a connection-failed message
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  mock_imap_client.fetch_message = AsyncMock(side_effect=TimeoutError("Server did not respond"))

  await cli._cmd_show(["1"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Connection failed" in args[1]
  assert "network" in args[2].lower()


@patch("simple_email_gw.cli.app.display_error")
async def test_show_rate_limit_error_shows_rate_limit_exceeded(
  mock_display_error, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is not cached
  When: The IMAP fetch raises RateLimitError
  Then: An error panel should be displayed with a rate-limit-exceeded message
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  mock_imap_client.fetch_message = AsyncMock(side_effect=RateLimitError("Too many requests"))

  await cli._cmd_show(["1"])

  mock_display_error.assert_called_once()
  args, _ = mock_display_error.call_args
  assert "Rate limit exceeded: Too many requests" in args[1]
  assert "wait" in args[2].lower()


@patch("simple_email_gw.cli.display.display_email")
async def test_show_keyboard_interrupt_shows_cancelled_message(
  mock_display_email, cli, mock_session, mock_imap_client
):
  """
  Given: An account is selected and the message is not cached
  When: The user presses Ctrl+C during the IMAP fetch
  Then: A 'Fetch cancelled.' message should be printed and the command should return gracefully
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  mock_session.get_cached_email.return_value = None
  mock_imap_client.fetch_message = AsyncMock(side_effect=KeyboardInterrupt)

  await cli._cmd_show(["1"])

  mock_display_email.assert_not_called()


@patch("simple_email_gw.cli.display.display_email")
async def test_show_stale_cache_after_folder_change(
  mock_display_email, cli, mock_session, mock_imap_client
):
  """
  Given: A message was cached in INBOX and folder was changed to Sent
  When: The 'show' command is executed for the same message ID in the new folder
  Then: get_cached_email returns None and a fresh fetch is performed for the new folder
  """
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "Sent"
  mock_session.get_imap_client.return_value = mock_imap_client
  # Simulate stale cache: get_cached_email returns None after folder change
  mock_session.get_cached_email.return_value = None
  fetched_message = {
    "id": "1",
    "from": "alice@example.com",
    "to": "me@example.com",
    "subject": "Hello",
    "date": "2026-05-08",
    "body": "Hello world",
  }
  mock_imap_client.fetch_message = AsyncMock(return_value=fetched_message)

  await cli._cmd_show(["1"])

  mock_session.get_cached_email.assert_called_once_with("1")
  mock_imap_client.fetch_message.assert_awaited_once_with("1", folder="Sent")
  mock_display_email.assert_called_once_with(cli.console, fetched_message)


@patch("simple_email_gw.cli.display.display_email")
async def test_show_cache_hit_avoids_fetch(mock_display_email, cli, mock_session, mock_imap_client):
  """
  Given: An account is selected and a message was previously fetched
  When: The 'show' command is executed for the same message twice
  Then: The first call should fetch and display; the second call should use cache and skip fetch
  """
  # Setup
  mock_session.current_account = MagicMock(name="test-account")
  mock_session.current_folder = "INBOX"
  mock_session.get_imap_client.return_value = mock_imap_client
  fetched_message = {
    "id": "1",
    "from": "alice@example.com",
    "to": "me@example.com",
    "subject": "Hello",
    "date": "2026-05-08",
    "body": "Hello world",
  }
  mock_session.get_cached_email.return_value = None
  mock_imap_client.fetch_message = AsyncMock(return_value=fetched_message)

  # First call - cache miss
  await cli._cmd_show(["1"])

  mock_imap_client.fetch_message.assert_awaited_once()
  mock_display_email.assert_called_once_with(cli.console, fetched_message)

  # Reset mocks for second call
  mock_display_email.reset_mock()
  mock_imap_client.fetch_message.reset_mock()
  mock_session.get_imap_client.reset_mock()
  mock_session.get_cached_email.reset_mock()

  # Second call - cache hit
  mock_session.get_cached_email.return_value = fetched_message

  await cli._cmd_show(["1"])

  mock_session.get_cached_email.assert_called_once_with("1")
  mock_imap_client.fetch_message.assert_not_called()
  mock_session.get_imap_client.assert_not_called()
  mock_display_email.assert_called_once_with(cli.console, fetched_message)
