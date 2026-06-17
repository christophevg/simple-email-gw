"""Tests for audit logging helpers."""

import logging
from unittest.mock import patch

from simple_email_gw.safety.audit import log_email_appended


class TestLogEmailAppended:
  """Tests for log_email_appended audit helper."""

  def test_log_email_appended_success(self):
    """Test successful append is logged at INFO level."""
    with patch("simple_email_gw.safety.audit.log_event") as mock_log:
      log_email_appended(
        account="test",
        folder="Sent",
        success=True,
        message_id="<msg123@example.com>",
        subject_prefix="Hello",
        message_size=1234,
        auto_append=False,
      )

      mock_log.assert_called_once()
      args = mock_log.call_args
      assert args.kwargs["event"] == "EMAIL_APPENDED"
      assert args.kwargs["account"] == "test"
      assert args.kwargs["level"] == logging.INFO
      details = args.kwargs["details"]
      assert details["folder"] == "Sent"
      assert details["message_id"] == "<msg123@example.com>"
      assert details["subject_prefix"] == "Hello"
      assert details["message_size"] == 1234
      assert details["auto_append"] is False
      assert details["success"] is True
      assert details["error"] is None

  def test_log_email_appended_failure(self):
    """Test failed append is logged at WARNING level with error."""
    with patch("simple_email_gw.safety.audit.log_event") as mock_log:
      log_email_appended(
        account="test",
        folder="Sent",
        success=False,
        message_id="<msg123@example.com>",
        subject_prefix="Hello",
        message_size=1234,
        auto_append=True,
        error="Sent folder not found",
      )

      args = mock_log.call_args
      assert args.kwargs["level"] == logging.WARNING
      assert args.kwargs["details"]["success"] is False
      assert args.kwargs["details"]["error"] == "Sent folder not found"
      assert args.kwargs["details"]["auto_append"] is True

  def test_log_email_appended_truncates_long_fields(self):
    """Test long message_id and subject are truncated to 50 characters."""
    with patch("simple_email_gw.safety.audit.log_event") as mock_log:
      log_email_appended(
        account="test",
        folder="Sent",
        message_id="x" * 100,
        subject_prefix="y" * 100,
      )

      details = mock_log.call_args.kwargs["details"]
      assert len(details["message_id"]) == 50
      assert len(details["subject_prefix"]) == 50

  def test_log_email_appended_boundary_50_not_truncated(self):
    """Exactly 50 characters are preserved."""
    with patch("simple_email_gw.safety.audit.log_event") as mock_log:
      log_email_appended(
        account="test",
        folder="Sent",
        message_id="x" * 50,
        subject_prefix="y" * 50,
      )

      details = mock_log.call_args.kwargs["details"]
      assert details["message_id"] == "x" * 50
      assert details["subject_prefix"] == "y" * 50

  def test_log_email_appended_boundary_51_truncated(self):
    """51 characters are truncated to 50."""
    with patch("simple_email_gw.safety.audit.log_event") as mock_log:
      log_email_appended(
        account="test",
        folder="Sent",
        message_id="x" * 51,
        subject_prefix="y" * 51,
      )

      details = mock_log.call_args.kwargs["details"]
      assert len(details["message_id"]) == 50
      assert len(details["subject_prefix"]) == 50
