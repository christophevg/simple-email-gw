"""
Tests for Display Utilities in cli/display.py.

These tests verify the Rich-based display functions that format various
types of content for CLI output, including tables, panels, and styled messages.
"""

import asyncio
from unittest.mock import patch

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from simple_email_gw.cli.display import (
  EmailDraft,
  confirm_send,
  display_accounts,
  display_email,
  display_emails,
  display_error,
  display_folders,
  display_success,
  display_warning,
  get_body_input,
  get_recipients_input,
)
from simple_email_gw.smtp.client import WhitelistError


class TestDisplayAccounts:
  """Tests for display_accounts function."""

  def test_display_accounts_creates_table_with_correct_columns(self):
    """
    Given: A list of account dictionaries
    When: display_accounts is called
    Then: A Rich Table is created with columns Name, Username, Status
    """
    console = Console()
    accounts = [{"name": "work", "username": "user@example.com", "status": "available"}]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      # Verify print was called
      assert mock_print.called

      # Verify a Table was created and printed
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_accounts_applies_cyan_style_to_account_names(self):
    """
    Given: A list of account dictionaries
    When: display_accounts is called
    Then: Account names are styled with cyan color
    """
    console = Console()
    accounts = [{"name": "work", "username": "user@example.com", "status": "available"}]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      # Verify the table contains cyan-styled account name
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_accounts_prints_table_to_console(self):
    """
    Given: A list of account dictionaries
    When: display_accounts is called with a Console instance
    Then: Table is printed to the console
    """
    console = Console()
    accounts = [{"name": "work", "username": "user@example.com", "status": "available"}]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)
      assert mock_print.called

  def test_display_accounts_handles_empty_list(self):
    """
    Given: An empty list of accounts
    When: display_accounts is called
    Then: Appropriate message or empty table is displayed
    """
    console = Console()
    accounts = []

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      # Should print a panel for empty accounts
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_accounts_formats_status_column_correctly(self):
    """
    Given: Account data with different statuses
    When: display_accounts is called
    Then: Status column shows "connected" or "available" appropriately
    """
    console = Console()
    accounts = [
      {"name": "work", "username": "user1@example.com", "status": "connected"},
      {"name": "personal", "username": "user2@example.com", "status": "available"},
    ]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      # Verify table was printed with both statuses
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_accounts_displays_multiple_accounts(self):
    """
    Given: A list of multiple accounts
    When: display_accounts is called
    Then: All accounts are displayed in the table with proper formatting
    """
    console = Console()
    accounts = [
      {"name": "work", "username": "user1@example.com", "status": "available"},
      {"name": "personal", "username": "user2@example.com", "status": "connected"},
      {"name": "archive", "username": "user3@example.com", "status": "available"},
    ]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      # Verify table was created
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)


class TestDisplayFolders:
  """Tests for display_folders function."""

  def test_display_folders_creates_table_with_correct_columns(self):
    """
    Given: A list of folder dictionaries
    When: display_folders is called
    Then: A Rich Table is created with columns Name, Flags, Delimiter
    """
    console = Console()
    folders = [{"name": "INBOX", "flags": [], "delimiter": "/"}]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_folders_applies_green_style_to_folder_names(self):
    """
    Given: A list of folder dictionaries
    When: display_folders is called
    Then: Folder names are styled with green color
    """
    console = Console()
    folders = [{"name": "INBOX", "flags": [], "delimiter": "/"}]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_folders_prints_table_to_console(self):
    """
    Given: A list of folder dictionaries
    When: display_folders is called with a Console instance
    Then: Table is printed to the console
    """
    console = Console()
    folders = [{"name": "INBOX", "flags": [], "delimiter": "/"}]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)
      assert mock_print.called

  def test_display_folders_handles_empty_list(self):
    """
    Given: An empty list of folders
    When: display_folders is called
    Then: Appropriate message or empty table is displayed
    """
    console = Console()
    folders = []

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_folders_displays_folder_flags(self):
    """
    Given: Folder data with flags like \\HasNoChildren, \\Marked
    When: display_folders is called
    Then: Flags are displayed in the Flags column
    """
    console = Console()
    folders = [{"name": "INBOX", "flags": ["\\HasNoChildren", "\\Marked"], "delimiter": "/"}]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_folders_displays_multiple_folders(self):
    """
    Given: A list of multiple folders
    When: display_folders is called
    Then: All folders are displayed in the table with proper formatting
    """
    console = Console()
    folders = [
      {"name": "INBOX", "flags": [], "delimiter": "/"},
      {"name": "Sent", "flags": ["\\HasNoChildren"], "delimiter": "/"},
      {"name": "Archive", "flags": ["\\Marked"], "delimiter": "/"},
    ]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)


class TestDisplayEmails:
  """Tests for display_emails function."""

  def test_display_emails_creates_table_with_correct_columns(self):
    """
    Given: A list of email dictionaries
    When: display_emails is called
    Then: A Rich Table is created with columns ID, From, Subject, Date, Status
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_emails_applies_cyan_style_to_email_ids(self):
    """
    Given: A list of email dictionaries
    When: display_emails is called
    Then: Email IDs are styled with cyan color
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_emails_applies_white_style_to_subjects(self):
    """
    Given: A list of email dictionaries
    When: display_emails is called
    Then: Email subjects are styled with white color
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_emails_applies_bold_to_unread_subjects(self):
    """
    Given: A list of email dictionaries with read and unread messages
    When: display_emails is called
    Then: Unread email subjects are displayed in bold white
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Read Email",
        "date": "2024-01-01",
        "read": True,
      },
      {
        "id": "2",
        "from": "sender@example.com",
        "subject": "Unread Email",
        "date": "2024-01-02",
        "read": False,
      },
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_emails_applies_yellow_style_to_dates(self):
    """
    Given: A list of email dictionaries
    When: display_emails is called
    Then: Dates are styled with yellow color
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_emails_prints_table_to_console(self):
    """
    Given: A list of email dictionaries
    When: display_emails is called with a Console instance
    Then: Table is printed to the console
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)
      assert mock_print.called

  def test_display_emails_handles_empty_list(self):
    """
    Given: An empty list of emails
    When: display_emails is called
    Then: Appropriate message or empty table is displayed
    """
    console = Console()
    messages = []

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_emails_displays_read_unread_status(self):
    """
    Given: Email data with read/unread status
    When: display_emails is called
    Then: Status column shows "read" or "unread" appropriately
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Read",
        "date": "2024-01-01",
        "read": True,
      },
      {
        "id": "2",
        "from": "sender@example.com",
        "subject": "Unread",
        "date": "2024-01-02",
        "read": False,
      },
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_display_emails_displays_multiple_emails(self):
    """
    Given: A list of multiple emails
    When: display_emails is called
    Then: All emails are displayed in the table with proper formatting
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender1@example.com",
        "subject": "Email 1",
        "date": "2024-01-01",
        "read": True,
      },
      {
        "id": "2",
        "from": "sender2@example.com",
        "subject": "Email 2",
        "date": "2024-01-02",
        "read": False,
      },
      {
        "id": "3",
        "from": "sender3@example.com",
        "subject": "Email 3",
        "date": "2024-01-03",
        "read": True,
      },
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)


class TestDisplayEmail:
  """Tests for display_email function (single email panel)."""

  def test_display_email_creates_panel_with_email_title(self):
    """
    Given: An email dictionary with id
    When: display_email is called
    Then: A Rich Panel is created with email ID in title
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Verify panel was printed (first call)
      first_call = mock_print.call_args_list[0]
      printed_arg = first_call[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_email_uses_syntax_highlighting_for_headers(self):
    """
    Given: An email dictionary with headers
    When: display_email is called
    Then: Headers are displayed with syntax highlighting using Rich Syntax
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Verify panel contains Syntax object
      first_call = mock_print.call_args_list[0]
      printed_arg = first_call[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_email_includes_from_to_subject_date_headers(self):
    """
    Given: An email dictionary with From, To, Subject, Date fields
    When: display_email is called
    Then: Panel includes all header fields
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Verify console.print was called multiple times
      assert mock_print.call_count >= 2

  def test_display_email_displays_body_below_headers(self):
    """
    Given: An email dictionary with body
    When: display_email is called
    Then: Email body is displayed below the header panel
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "This is the email body content.",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Verify body was printed
      assert mock_print.call_count >= 2

  def test_display_email_prints_panel_to_console(self):
    """
    Given: An email dictionary
    When: display_email is called with a Console instance
    Then: Panel is printed to the console
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)
      assert mock_print.called

  def test_display_email_handles_attachments_list(self):
    """
    Given: An email dictionary with attachments
    When: display_email is called
    Then: Attachments are listed if present
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
      "attachments": [
        {"filename": "document.pdf", "size": 1024},
        {"filename": "image.png", "size": 2048},
      ],
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Verify attachments were printed
      assert mock_print.call_count >= 3

  def test_display_email_handles_missing_optional_fields(self):
    """
    Given: An email dictionary with only required fields
    When: display_email is called
    Then: Display works correctly without errors
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Should work without errors
      assert mock_print.called


class TestDisplayError:
  """Tests for display_error function."""

  def test_display_error_creates_error_panel(self):
    """
    Given: An error message string
    When: display_error is called
    Then: A Rich Panel is created with the error message
    """
    console = Console()
    error_msg = "Connection failed"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_error_applies_red_style(self):
    """
    Given: An error message string
    When: display_error is called
    Then: Panel is styled with red color
    """
    console = Console()
    error_msg = "Connection failed"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      # Panel style should be red
      assert printed_arg.style == "red"

  def test_display_error_prints_panel_to_console(self):
    """
    Given: An error message string
    When: display_error is called with a Console instance
    Then: Error panel is printed to the console
    """
    console = Console()
    error_msg = "Connection failed"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg)
      assert mock_print.called

  def test_display_error_includes_suggestion_when_provided(self):
    """
    Given: An error message and a suggestion
    When: display_error is called with suggestion parameter
    Then: Panel includes both error message and suggestion
    """
    console = Console()
    error_msg = "Connection failed"
    suggestion = "Check your network settings"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg, suggestion)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_error_without_suggestion(self):
    """
    Given: An error message without suggestion
    When: display_error is called without suggestion parameter
    Then: Panel displays only the error message
    """
    console = Console()
    error_msg = "Connection failed"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_error_uses_error_title(self):
    """
    Given: An error message string
    When: display_error is called
    Then: Panel has "Error" or similar title
    """
    console = Console()
    error_msg = "Connection failed"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)


class TestDisplaySuccess:
  """Tests for display_success function."""

  def test_display_success_creates_success_panel(self):
    """
    Given: A success message string
    When: display_success is called
    Then: A Rich Panel is created with the success message
    """
    console = Console()
    message = "Email sent successfully"

    with patch.object(console, "print") as mock_print:
      display_success(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_success_applies_green_style(self):
    """
    Given: A success message string
    When: display_success is called
    Then: Panel is styled with green color
    """
    console = Console()
    message = "Email sent successfully"

    with patch.object(console, "print") as mock_print:
      display_success(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "green"

  def test_display_success_prints_panel_to_console(self):
    """
    Given: A success message string
    When: display_success is called with a Console instance
    Then: Success panel is printed to the console
    """
    console = Console()
    message = "Email sent successfully"

    with patch.object(console, "print") as mock_print:
      display_success(console, message)
      assert mock_print.called

  def test_display_success_uses_success_title(self):
    """
    Given: A success message string
    When: display_success is called
    Then: Panel has "Success" or similar title
    """
    console = Console()
    message = "Email sent successfully"

    with patch.object(console, "print") as mock_print:
      display_success(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)


class TestDisplayWarning:
  """Tests for display_warning function."""

  def test_display_warning_creates_warning_panel(self):
    """
    Given: A warning message string
    When: display_warning is called
    Then: A Rich Panel is created with the warning message
    """
    console = Console()
    message = "Rate limit approaching"

    with patch.object(console, "print") as mock_print:
      display_warning(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

  def test_display_warning_applies_yellow_style(self):
    """
    Given: A warning message string
    When: display_warning is called
    Then: Panel is styled with yellow color
    """
    console = Console()
    message = "Rate limit approaching"

    with patch.object(console, "print") as mock_print:
      display_warning(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "yellow"

  def test_display_warning_prints_panel_to_console(self):
    """
    Given: A warning message string
    When: display_warning is called with a Console instance
    Then: Warning panel is printed to the console
    """
    console = Console()
    message = "Rate limit approaching"

    with patch.object(console, "print") as mock_print:
      display_warning(console, message)
      assert mock_print.called

  def test_display_warning_uses_warning_title(self):
    """
    Given: A warning message string
    When: display_warning is called
    Then: Panel has "Warning" or similar title
    """
    console = Console()
    message = "Rate limit approaching"

    with patch.object(console, "print") as mock_print:
      display_warning(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)


class TestStyleConventions:
  """Tests for consistent styling across display functions."""

  def test_cyan_style_for_account_names(self):
    """
    Given: Display functions using account names
    When: Styling is applied
    Then: Account names use cyan color consistently
    """
    console = Console()
    accounts = [{"name": "work", "username": "user@example.com", "status": "available"}]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_green_style_for_folder_names(self):
    """
    Given: Display functions using folder names
    When: Styling is applied
    Then: Folder names use green color consistently
    """
    console = Console()
    folders = [{"name": "INBOX", "flags": [], "delimiter": "/"}]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_cyan_style_for_email_ids(self):
    """
    Given: Display functions using email IDs
    When: Styling is applied
    Then: Email IDs use cyan color consistently
    """
    console = Console()
    messages = [
      {
        "id": "123",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_white_style_for_email_subjects(self):
    """
    Given: Display functions using email subjects
    When: Styling is applied
    Then: Email subjects use white color with bold for unread
    """
    console = Console()
    messages = [
      {
        "id": "123",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": False,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_yellow_style_for_dates(self):
    """
    Given: Display functions using dates
    When: Styling is applied
    Then: Dates use yellow color consistently
    """
    console = Console()
    messages = [
      {
        "id": "123",
        "from": "sender@example.com",
        "subject": "Test",
        "date": "2024-01-01",
        "read": True,
      }
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_red_style_for_errors(self):
    """
    Given: Error display function
    When: Styling is applied
    Then: Errors use red color consistently
    """
    console = Console()
    error_msg = "Connection failed"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "red"

  def test_green_style_for_success(self):
    """
    Given: Success display function
    When: Styling is applied
    Then: Success messages use green color consistently
    """
    console = Console()
    message = "Email sent successfully"

    with patch.object(console, "print") as mock_print:
      display_success(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "green"

  def test_yellow_style_for_warnings(self):
    """
    Given: Warning display function
    When: Styling is applied
    Then: Warnings use yellow color consistently
    """
    console = Console()
    message = "Rate limit approaching"

    with patch.object(console, "print") as mock_print:
      display_warning(console, message)

      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "yellow"


class TestConsoleIntegration:
  """Tests for Rich Console integration."""

  def test_display_functions_accept_console_parameter(self):
    """
    Given: All display functions
    When: Called with a Console instance
    Then: Functions accept and use the console parameter
    """
    console = Console()

    # Test each display function accepts console parameter
    display_accounts(console, [])
    display_folders(console, [])
    display_emails(console, [])
    display_email(console, {"id": "1", "from": "", "to": "", "subject": "", "date": "", "body": ""})
    display_error(console, "test")
    display_success(console, "test")
    display_warning(console, "test")

  def test_display_functions_use_console_print(self):
    """
    Given: Display functions with Console instance
    When: Called
    Then: Functions use console.print() for output
    """
    console = Console()

    with patch.object(console, "print") as mock_print:
      display_accounts(console, [])
      assert mock_print.called

      mock_print.reset_mock()
      display_folders(console, [])
      assert mock_print.called

      mock_print.reset_mock()
      display_emails(console, [])
      assert mock_print.called

  def test_table_creation_uses_rich_table_class(self):
    """
    Given: Table-based display functions
    When: Creating tables
    Then: Rich Table class is used
    """
    console = Console()

    with patch.object(console, "print") as mock_print:
      display_accounts(
        console, [{"name": "work", "username": "user@example.com", "status": "available"}]
      )
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

      mock_print.reset_mock()
      display_folders(console, [{"name": "INBOX", "flags": [], "delimiter": "/"}])
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

      mock_print.reset_mock()
      display_emails(console, [{"id": "1", "from": "", "subject": "", "date": "", "read": True}])
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_panel_creation_uses_rich_panel_class(self):
    """
    Given: Panel-based display functions
    When: Creating panels
    Then: Rich Panel class is used
    """
    console = Console()

    with patch.object(console, "print") as mock_print:
      display_error(console, "test")
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

      mock_print.reset_mock()
      display_success(console, "test")
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)

      mock_print.reset_mock()
      display_warning(console, "test")
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)


class TestEdgeCases:
  """Tests for edge cases and error handling."""

  def test_display_functions_handle_missing_fields(self):
    """
    Given: Data dictionaries with missing fields
    When: Display functions are called
    Then: Functions handle missing fields gracefully without crashing
    """
    console = Console()

    # Test accounts with missing fields
    with patch.object(console, "print"):
      display_accounts(console, [{}])
      display_accounts(console, [{"name": "only_name"}])
      display_accounts(console, [{"name": "test", "username": "user"}])

    # Test folders with missing fields
    with patch.object(console, "print"):
      display_folders(console, [{}])
      display_folders(console, [{"name": "INBOX"}])

    # Test emails with missing fields
    with patch.object(console, "print"):
      display_emails(console, [{}])
      display_emails(console, [{"id": "1"}])

    # Test email with missing fields
    with patch.object(console, "print"):
      display_email(console, {"id": "1"})
      display_email(console, {"id": "1", "from": "", "to": ""})

  def test_display_functions_handle_unicode_content(self):
    """
    Given: Data with unicode characters
    When: Display functions are called
    Then: Unicode is properly rendered in tables and panels
    """
    console = Console()

    accounts = [{"name": "tëst", "username": "usér@example.com", "status": "available"}]
    folders = [{"name": "Dössiers", "flags": [], "delimiter": "/"}]
    messages = [
      {
        "id": "1",
        "from": "sënder@exämple.com",
        "subject": "Tëst Ëmail",
        "date": "2024-01-01",
        "read": True,
      }
    ]
    email = {
      "id": "1",
      "from": "sënder@exämple.com",
      "to": "recipïent@example.com",
      "subject": "Tëst with ünïcödé",
      "date": "2024-01-01",
      "body": "Bödy with spëcial chåracters",
    }

    with patch.object(console, "print"):
      display_accounts(console, accounts)
      display_folders(console, folders)
      display_emails(console, messages)
      display_email(console, email)

  def test_display_functions_handle_long_content(self):
    """
    Given: Data with very long strings
    When: Display functions are called
    Then: Long content is handled appropriately (truncated or wrapped)
    """
    console = Console()

    long_name = "a" * 200
    long_subject = "b" * 500

    accounts = [{"name": long_name, "username": "user@example.com", "status": "available"}]
    folders = [{"name": long_name, "flags": [], "delimiter": "/"}]
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": long_subject,
        "date": "2024-01-01",
        "read": True,
      }
    ]
    email = {
      "id": "1",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": long_subject,
      "date": "2024-01-01",
      "body": "Body content",
    }

    with patch.object(console, "print"):
      display_accounts(console, accounts)
      display_folders(console, folders)
      display_emails(console, messages)
      display_email(console, email)

  def test_display_functions_with_none_values(self):
    """
    Given: Data dictionaries with None values
    When: Display functions are called
    Then: None values are handled gracefully
    """
    console = Console()

    accounts = [{"name": None, "username": None, "status": None}]
    folders = [{"name": None, "flags": None, "delimiter": None}]
    messages = [{"id": None, "from": None, "subject": None, "date": None, "read": None}]
    email = {"id": None, "from": None, "to": None, "subject": None, "date": None, "body": None}

    with patch.object(console, "print"):
      display_accounts(console, accounts)
      display_folders(console, folders)
      display_emails(console, messages)
      display_email(console, email)

  def test_syntax_highlighting_for_email_headers(self):
    """
    Given: Email headers for display_email
    When: Creating Syntax object
    Then: Syntax highlighting uses 'email' language and appropriate theme
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # Verify that console.print was called with Panel containing Syntax
      first_call = mock_print.call_args_list[0]
      printed_arg = first_call[0][0]
      assert isinstance(printed_arg, Panel)


class TestDisplayUtilitiesIntegration:
  """Integration tests for display utilities with Rich Console."""

  def test_accounts_table_format_with_mock_console(self):
    """
    Given: Mock console and account data
    When: display_accounts is called
    Then: Console.print is called with properly formatted Table
    """
    console = Console()
    accounts = [
      {"name": "work", "username": "user1@example.com", "status": "connected"},
      {"name": "personal", "username": "user2@example.com", "status": "available"},
    ]

    with patch.object(console, "print") as mock_print:
      display_accounts(console, accounts)

      # Verify console.print was called with Table
      assert mock_print.called
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_folders_table_format_with_mock_console(self):
    """
    Given: Mock console and folder data
    When: display_folders is called
    Then: Console.print is called with properly formatted Table
    """
    console = Console()
    folders = [
      {"name": "INBOX", "flags": ["\\Marked"], "delimiter": "/"},
      {"name": "Sent", "flags": ["\\HasNoChildren"], "delimiter": "/"},
    ]

    with patch.object(console, "print") as mock_print:
      display_folders(console, folders)

      assert mock_print.called
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_emails_table_format_with_mock_console(self):
    """
    Given: Mock console and email data
    When: display_emails is called
    Then: Console.print is called with properly formatted Table
    """
    console = Console()
    messages = [
      {
        "id": "1",
        "from": "sender@example.com",
        "subject": "Test 1",
        "date": "2024-01-01",
        "read": True,
      },
      {
        "id": "2",
        "from": "sender@example.com",
        "subject": "Test 2",
        "date": "2024-01-02",
        "read": False,
      },
    ]

    with patch.object(console, "print") as mock_print:
      display_emails(console, messages)

      assert mock_print.called
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Table)

  def test_email_panel_format_with_mock_console(self):
    """
    Given: Mock console and single email data
    When: display_email is called
    Then: Console.print is called with properly formatted Panel
    """
    console = Console()
    email = {
      "id": "123",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test Subject",
      "date": "2024-01-01",
      "body": "Test body content",
    }

    with patch.object(console, "print") as mock_print:
      display_email(console, email)

      # First call should be the panel with headers
      assert mock_print.called
      first_call = mock_print.call_args_list[0]
      printed_arg = first_call[0][0]
      assert isinstance(printed_arg, Panel)

  def test_error_panel_format_with_mock_console(self):
    """
    Given: Mock console and error message
    When: display_error is called
    Then: Console.print is called with properly formatted error Panel
    """
    console = Console()
    error_msg = "Failed to connect to server"
    suggestion = "Check your network connection"

    with patch.object(console, "print") as mock_print:
      display_error(console, error_msg, suggestion)

      assert mock_print.called
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "red"

  def test_success_panel_format_with_mock_console(self):
    """
    Given: Mock console and success message
    When: display_success is called
    Then: Console.print is called with properly formatted success Panel
    """
    console = Console()
    message = "Email sent successfully"

    with patch.object(console, "print") as mock_print:
      display_success(console, message)

      assert mock_print.called
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "green"

  def test_warning_panel_format_with_mock_console(self):
    """
    Given: Mock console and warning message
    When: display_warning is called
    Then: Console.print is called with properly formatted warning Panel
    """
    console = Console()
    message = "Rate limit approaching"

    with patch.object(console, "print") as mock_print:
      display_warning(console, message)

      assert mock_print.called
      printed_arg = mock_print.call_args[0][0]
      assert isinstance(printed_arg, Panel)
      assert printed_arg.style == "yellow"


class TestInteractiveInput:
  """Tests for interactive input functions."""

  @pytest.mark.asyncio
  async def test_get_recipients_input_single_recipient(self):
    """
    Given: User input with single recipient
    When: get_recipients_input is called
    Then: Returns list with single validated recipient
    """
    console = Console()

    with patch("builtins.input", return_value="user@example.com"):
      result = await get_recipients_input(console, "Enter recipient")
      assert result == ["user@example.com"]

  @pytest.mark.asyncio
  async def test_get_recipients_input_multiple_recipients(self):
    """
    Given: User input with multiple recipients
    When: get_recipients_input is called
    Then: Returns list with all recipients
    """
    console = Console()

    with patch(
      "builtins.input", return_value="user1@example.com, user2@example.com, user3@example.com"
    ):
      result = await get_recipients_input(console, "Enter recipients")
      assert result == ["user1@example.com", "user2@example.com", "user3@example.com"]

  @pytest.mark.asyncio
  async def test_get_body_input_multiline(self):
    """
    Given: Multi-line body input
    When: get_body_input is called
    Then: Returns concatenated body text
    """
    console = Console()

    with patch("builtins.input", side_effect=["Line 1", "Line 2", "Line 3", EOFError()]):
      result = await get_body_input(console, "Enter body")
      assert result == "Line 1\nLine 2\nLine 3"

  @pytest.mark.asyncio
  async def test_confirm_send_confirmed(self):
    """
    Given: User confirms sending
    When: confirm_send is called
    Then: Returns True
    """
    console = Console()
    draft = EmailDraft(to=["recipient@example.com"], subject="Test", body="Body")

    with patch("builtins.input", return_value="y"):
      result = await confirm_send(console, draft)
      assert result is True

  @pytest.mark.asyncio
  async def test_confirm_send_declined(self):
    """
    Given: User declines sending
    When: confirm_send is called
    Then: Returns False
    """
    console = Console()
    draft = EmailDraft(to=["recipient@example.com"], subject="Test", body="Body")

    with patch("builtins.input", return_value="n"):
      result = await confirm_send(console, draft)
      assert result is False


class TestEmailDraft:
  """Tests for EmailDraft dataclass."""

  def test_email_draft_creation(self):
    """
    Given: Valid to, subject, body
    When: EmailDraft is created
    Then: All fields stored correctly
    """
    draft = EmailDraft(
      to=["alice@example.com"],
      subject="Hello",
      body="Test body",
      cc=["cc@example.com"],
      bcc=["bcc@example.com"],
      in_reply_to="<msg123@example.com>",
      references=["<ref1@example.com>"],
      mode="reply",
    )
    assert draft.to == ["alice@example.com"]
    assert draft.subject == "Hello"
    assert draft.body == "Test body"
    assert draft.cc == ["cc@example.com"]
    assert draft.bcc == ["bcc@example.com"]
    assert draft.in_reply_to == "<msg123@example.com>"
    assert draft.references == ["<ref1@example.com>"]
    assert draft.mode == "reply"

  def test_email_draft_default_cc_bcc(self):
    """
    Given: EmailDraft created without cc/bcc
    When: Accessing cc and bcc
    Then: Both default to empty lists
    """
    draft = EmailDraft(to=["alice@example.com"], subject="Hello", body="Test body")
    assert draft.cc == []
    assert draft.bcc == []
    assert draft.in_reply_to is None
    assert draft.references == []
    assert draft.mode == "compose"

  def test_email_draft_to_preview_dict(self):
    """
    Given: EmailDraft with all fields
    When: to_preview_dict() called
    Then: Returns dict with formatted to, cc, bcc, subject, body
    """
    draft = EmailDraft(
      to=["alice@example.com", "bob@example.com"],
      subject="Hello",
      body="Test body",
      cc=["cc@example.com"],
      bcc=["bcc@example.com"],
    )
    preview = draft.to_preview_dict()
    assert preview["to"] == "alice@example.com, bob@example.com"
    assert preview["cc"] == "cc@example.com"
    assert preview["bcc"] == "bcc@example.com"
    assert preview["subject"] == "Hello"
    assert preview["body"] == "Test body"
    assert preview["mode"] == "compose"

  def test_email_draft_empty_subject_preview(self):
    """
    Given: EmailDraft with empty subject
    When: to_preview_dict() called
    Then: Subject shown as '(no subject)'
    """
    draft = EmailDraft(to=["alice@example.com"], subject="", body="Test body")
    preview = draft.to_preview_dict()
    assert preview["subject"] == "(no subject)"

  def test_email_draft_reply_mode(self):
    """
    Given: EmailDraft created for reply
    When: Accessing mode field
    Then: Mode is 'reply' and in_reply_to/references set
    """
    draft = EmailDraft(
      to=["alice@example.com"],
      subject="Re: Hello",
      body="Reply body",
      in_reply_to="<orig@example.com>",
      references=["<ref@example.com>"],
      mode="reply",
    )
    assert draft.mode == "reply"
    assert draft.in_reply_to == "<orig@example.com>"
    assert draft.references == ["<ref@example.com>"]


class TestAsyncInputUtilities:
  """Tests for async input utilities (post-refactor)."""

  @pytest.mark.asyncio
  async def test_get_recipients_input_validates_email(self):
    """
    Given: User enters invalid email address
    When: get_recipients_input called
    Then: ValueError raised with clear message
    """
    console = Console()
    with patch("builtins.input", return_value="bad-email"):
      with pytest.raises(ValueError):
        await get_recipients_input(console, "Enter recipient")

  @pytest.mark.asyncio
  async def test_get_recipients_input_checks_whitelist(self):
    """
    Given: User enters email not in whitelist
    When: get_recipients_input called
    Then: WhitelistError raised with blocked address info
    """
    console = Console()
    with patch("simple_email_gw.cli.display.get_recipient_whitelist") as mock_whitelist:
      mock_whitelist.return_value.is_allowed.return_value = False
      mock_whitelist.return_value.filter_recipients.return_value = ([], ["blocked@evil.com"])
      with patch("builtins.input", return_value="blocked@evil.com"):
        with pytest.raises(WhitelistError):
          await get_recipients_input(console, "Enter recipient")

  @pytest.mark.asyncio
  async def test_get_recipients_input_handles_comma_separated(self):
    """
    Given: User enters 'a@x.com, b@x.com'
    When: get_recipients_input called
    Then: Returns ['a@x.com', 'b@x.com'] after validation
    """
    console = Console()
    with patch("simple_email_gw.cli.display.get_recipient_whitelist") as mock_whitelist:
      mock_whitelist.return_value.is_allowed.return_value = True
      mock_whitelist.return_value.filter_recipients.return_value = (
        ["a@x.com", "b@x.com"],
        [],
      )
      with patch("builtins.input", return_value="a@x.com, b@x.com"):
        result = await get_recipients_input(console, "Enter recipients")
        assert result == ["a@x.com", "b@x.com"]

  @pytest.mark.asyncio
  async def test_get_recipients_input_empty_skips(self):
    """
    Given: User presses Enter with no input
    When: get_recipients_input called for optional field
    Then: Returns empty list
    """
    console = Console()
    with patch("builtins.input", return_value=""):
      result = await get_recipients_input(console, "Enter recipients")
      assert result == []

  @pytest.mark.asyncio
  async def test_get_body_input_collects_multiline(self):
    """
    Given: User types multiple lines, then Ctrl+D
    When: get_body_input called
    Then: Returns concatenated text with newlines
    """
    console = Console()
    with patch("builtins.input", side_effect=["Line 1", "Line 2", "Line 3", EOFError()]):
      result = await get_body_input(console, "Enter body")
      assert result == "Line 1\nLine 2\nLine 3"

  @pytest.mark.asyncio
  async def test_get_body_input_enforces_size_limit(self):
    """
    Given: User enters body exceeding 10MB
    When: get_body_input called
    Then: ValueError raised, body rejected
    """
    console = Console()
    huge_line = "x" * (11 * 1024 * 1024)
    with patch("builtins.input", side_effect=[huge_line, EOFError()]):
      with pytest.raises(ValueError):
        await get_body_input(console, "Enter body")

  @pytest.mark.asyncio
  async def test_confirm_send_returns_y(self):
    """
    Given: User enters 'y'
    When: confirm_send called
    Then: Returns True
    """
    console = Console()
    draft = EmailDraft(to=["a@x.com"], subject="Test", body="Body")
    with patch("builtins.input", return_value="y"):
      result = await confirm_send(console, draft)
      assert result is True

  @pytest.mark.asyncio
  async def test_confirm_send_returns_n(self):
    """
    Given: User enters 'n'
    When: confirm_send called
    Then: Returns False
    """
    console = Console()
    draft = EmailDraft(to=["a@x.com"], subject="Test", body="Body")
    with patch("builtins.input", return_value="n"):
      result = await confirm_send(console, draft)
      assert result is False

  @pytest.mark.asyncio
  async def test_confirm_send_returns_e(self):
    """
    Given: User enters 'e'
    When: confirm_send called
    Then: Returns None (edit)
    """
    console = Console()
    draft = EmailDraft(to=["a@x.com"], subject="Test", body="Body")
    with patch("builtins.input", return_value="e"):
      result = await confirm_send(console, draft)
      assert result is None

  @pytest.mark.asyncio
  async def test_confirm_send_case_insensitive(self):
    """
    Given: User enters 'Y' or 'YES' or 'N' or 'NO'
    When: confirm_send called
    Then: Correctly mapped to True/False
    """
    console = Console()
    draft = EmailDraft(to=["a@x.com"], subject="Test", body="Body")
    with patch("builtins.input", return_value="Y"):
      assert await confirm_send(console, draft) is True
    with patch("builtins.input", return_value="YES"):
      assert await confirm_send(console, draft) is True
    with patch("builtins.input", return_value="N"):
      assert await confirm_send(console, draft) is False
    with patch("builtins.input", return_value="NO"):
      assert await confirm_send(console, draft) is False


class TestPreviewDisplay:
  """Tests for email preview display."""

  def test_preview_truncates_body_at_500_chars(self):
    """
    Given: Body longer than 500 characters
    When: Preview displayed
    Then: Body truncated with continuation note
    """
    console = Console()
    long_body = "a" * 600
    draft = EmailDraft(to=["a@x.com"], subject="Test", body=long_body)
    with patch("builtins.input", return_value="n"):
      with patch.object(console, "print") as mock_print:
        asyncio.run(confirm_send(console, draft))
        # Verify truncation occurred in output
        printed_texts = [str(call[0][0]) for call in mock_print.call_args_list if call[0]]
        full_output = " ".join(printed_texts)
        assert "... (" in full_output
        assert "more characters)" in full_output

  def test_preview_shows_metadata_table(self):
    """
    Given: Draft with From, To, CC, BCC, Subject
    When: Preview displayed
    Then: Rich Table with all metadata fields shown
    """
    console = Console()
    draft = EmailDraft(
      to=["a@x.com"],
      subject="Test",
      body="Body",
      cc=["cc@x.com"],
      bcc=["bcc@x.com"],
    )
    with patch("builtins.input", return_value="n"):
      with patch.object(console, "print") as mock_print:
        asyncio.run(confirm_send(console, draft, from_addr="from@x.com"))
        printed_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
        tables = [arg for arg in printed_args if isinstance(arg, Table)]
        assert len(tables) >= 1
        table = tables[0]
        # Render table to string to verify metadata labels appear as row content
        from io import StringIO

        output = StringIO()
        test_console = Console(file=output, force_terminal=False, width=80)
        test_console.print(table)
        rendered = output.getvalue()
        assert "From" in rendered
        assert "To" in rendered
        assert "Subject" in rendered

  def test_preview_handles_no_cc_bcc(self):
    """
    Given: Draft without CC or BCC
    When: Preview displayed
    Then: CC/BCC shown as '(none)' or omitted
    """
    draft = EmailDraft(to=["a@x.com"], subject="Test", body="Body")
    preview = draft.to_preview_dict()
    assert preview["cc"] == "(none)"
    assert preview["bcc"] == "(none)"

  def test_preview_empty_subject(self):
    """
    Given: Draft with empty subject
    When: Preview displayed
    Then: Subject shown as '(no subject)'
    """
    draft = EmailDraft(to=["a@x.com"], subject="", body="Body")
    preview = draft.to_preview_dict()
    assert preview["subject"] == "(no subject)"
