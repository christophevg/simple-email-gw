"""Tests for CRLF injection prevention."""

import pytest

from simple_email_gw.safety.sanitize import (
  APPEND_MAX_SIZE_DEFAULT,
  get_append_max_size,
  sanitize_filename,
  sanitize_folder_name,
  sanitize_header_value,
  sanitize_message_id,
  sanitize_message_id_numeric,
  sanitize_references,
  sanitize_subject,
  validate_append_flags,
  validate_folder_name,
)


class TestSanitizeMessageId:
  """Tests for sanitize_message_id function."""

  def test_valid_message_id(self):
    """Test valid Message-ID passes through."""
    result = sanitize_message_id("<abc123@mail.example.com>")
    assert result == "<abc123@mail.example.com>"

  def test_rejects_crlf(self):
    """Test CRLF sequences are rejected."""
    with pytest.raises(ValueError, match="newline characters"):
      sanitize_message_id("<valid@id.com>\r\nBcc: evil@attacker.com")

  def test_rejects_cr(self):
    """Test CR alone is rejected."""
    with pytest.raises(ValueError, match="newline characters"):
      sanitize_message_id("<valid@id.com>\rBcc: evil")

  def test_rejects_lf(self):
    """Test LF alone is rejected."""
    with pytest.raises(ValueError, match="newline characters"):
      sanitize_message_id("<valid@id.com>\nBcc: evil")

  def test_requires_angle_brackets(self):
    """Test Message-ID must be angle-bracketed."""
    with pytest.raises(ValueError, match="angle-bracketed"):
      sanitize_message_id("naked@id.com")

  def test_empty_rejected(self):
    """Test empty Message-ID is rejected."""
    with pytest.raises(ValueError, match="empty"):
      sanitize_message_id("")

  def test_nested_brackets_rejected(self):
    """Test nested angle brackets are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_message_id("<a<b>@domain.com>")


class TestSanitizeReferences:
  """Tests for sanitize_references function."""

  def test_valid_references(self):
    """Test valid references pass through."""
    result = sanitize_references(["<msg1@id.com>", "<msg2@id.com>"])
    assert result == ["<msg1@id.com>", "<msg2@id.com>"]

  def test_rejects_invalid_in_list(self):
    """Test invalid Message-ID in list is rejected."""
    with pytest.raises(ValueError, match="newline characters"):
      sanitize_references(["<valid@id.com>", "invalid\r\nEvil: yes"])


class TestSanitizeHeaderValue:
  """Tests for sanitize_header_value function."""

  def test_normal_value(self):
    """Test normal header value passes through."""
    result = sanitize_header_value("Normal Header Value")
    assert result == "Normal Header Value"

  def test_removes_crlf(self):
    """Test CRLF sequences are removed."""
    result = sanitize_header_value("Test\r\nInjected: evil")
    assert result == "TestInjected: evil"

  def test_removes_cr(self):
    """Test CR alone is removed."""
    result = sanitize_header_value("Test\rInjected")
    assert result == "TestInjected"

  def test_removes_lf(self):
    """Test LF alone is removed."""
    result = sanitize_header_value("Test\nInjected")
    assert result == "TestInjected"

  def test_empty_rejected(self):
    """Test empty value is rejected."""
    with pytest.raises(ValueError, match="empty"):
      sanitize_header_value("")


class TestSanitizeSubject:
  """Tests for sanitize_subject function."""

  def test_normal_subject(self):
    """Test normal subject passes through."""
    result = sanitize_subject("Normal Subject Line")
    assert result == "Normal Subject Line"

  def test_replaces_crlf_with_space(self):
    """Test CRLF is replaced with space."""
    result = sanitize_subject("Test\r\nBcc: attacker@evil.com")
    assert result == "Test Bcc: attacker@evil.com"

  def test_collapses_multiple_spaces(self):
    """Test multiple spaces are collapsed."""
    result = sanitize_subject("Test\r\n\r\nSubject")
    assert result == "Test Subject"

  def test_empty_rejected(self):
    """Test empty subject is rejected."""
    with pytest.raises(ValueError, match="empty"):
      sanitize_subject("")


class TestSanitizeFolderName:
  """Tests for sanitize_folder_name function."""

  def test_valid_folder_name(self):
    """Test valid folder name passes through."""
    result = sanitize_folder_name("INBOX")
    assert result == "INBOX"

  def test_valid_sent_folder(self):
    """Test valid Sent folder passes through."""
    result = sanitize_folder_name("Sent")
    assert result == "Sent"

  def test_rejects_crlf(self):
    """Test CRLF sequences are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_folder_name("INBOX\r\nNoop")

  def test_rejects_cr(self):
    """Test CR alone is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_folder_name("INBOX\rNoop")

  def test_rejects_lf(self):
    """Test LF alone is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_folder_name("INBOX\nNoop")


class TestSanitizeFilename:
  """Tests for sanitize_filename function."""

  def test_valid_filename(self):
    """Test valid filename passes through."""
    result = sanitize_filename("document.pdf")
    assert result == "document.pdf"

  def test_valid_filename_with_spaces(self):
    """Test filename with spaces passes through."""
    result = sanitize_filename("My Document.pdf")
    assert result == "My Document.pdf"

  def test_rejects_crlf(self):
    """Test CRLF sequences are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_filename("test.txt\r\nBcc: evil")

  def test_rejects_cr(self):
    """Test CR alone is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_filename("test.txt\rInjected")

  def test_rejects_lf(self):
    """Test LF alone is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_filename("test.txt\nInjected")

  def test_rejects_null(self):
    """Test null character is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      sanitize_filename("test\x00.txt")


class TestSanitizeMessageIdNumeric:
  """Tests for sanitize_message_id_numeric function."""

  def test_valid_numeric_id(self):
    """Test valid numeric ID passes through."""
    result = sanitize_message_id_numeric("123")
    assert result == "123"

  def test_valid_large_numeric_id(self):
    """Test valid large numeric ID passes through."""
    result = sanitize_message_id_numeric("999999")
    assert result == "999999"

  def test_rejects_non_numeric(self):
    """Test non-numeric ID is rejected."""
    with pytest.raises(ValueError, match="Invalid message ID"):
      sanitize_message_id_numeric("abc")

  def test_rejects_crlf_injection(self):
    """Test CRLF injection is rejected."""
    with pytest.raises(ValueError, match="Invalid message ID"):
      sanitize_message_id_numeric("1\r\nNoop")

  def test_rejects_special_chars(self):
    """Test special characters are rejected."""
    with pytest.raises(ValueError, match="Invalid message ID"):
      sanitize_message_id_numeric("1; DELETE *")

  def test_rejects_empty(self):
    """Test empty string is rejected."""
    with pytest.raises(ValueError, match="Invalid message ID"):
      sanitize_message_id_numeric("")

  def test_rejects_negative(self):
    """Test negative number is rejected."""
    with pytest.raises(ValueError, match="Invalid message ID"):
      sanitize_message_id_numeric("-1")


class TestValidateFolderName:
  """Tests for validate_folder_name function."""

  def test_valid_folder_name(self):
    """Test valid folder name passes through."""
    result = validate_folder_name("Archive")
    assert result == "Archive"

  def test_strips_whitespace(self):
    """Test leading/trailing whitespace is stripped."""
    result = validate_folder_name("  Archive  ")
    assert result == "Archive"

  def test_rejects_empty(self):
    """Test empty folder name is rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
      validate_folder_name("")

  def test_rejects_whitespace_only(self):
    """Test whitespace-only folder name is rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
      validate_folder_name("   ")

  def test_rejects_too_long(self):
    """Test folder name longer than 255 bytes is rejected."""
    long_name = "x" * 256
    with pytest.raises(ValueError, match="exceeds maximum length"):
      validate_folder_name(long_name)

  def test_rejects_crlf(self):
    """Test CRLF sequences are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      validate_folder_name("Bad\r\nFolder")

  def test_rejects_cr(self):
    """Test CR alone is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      validate_folder_name("Bad\rFolder")

  def test_rejects_lf(self):
    """Test LF alone is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      validate_folder_name("Bad\nFolder")

  def test_rejects_null(self):
    """Test null character is rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      validate_folder_name("Bad\x00Folder")

  def test_rejects_quotes(self):
    """Test double quotes are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      validate_folder_name('Bad"Folder')

  def test_rejects_backslash(self):
    """Test backslashes are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
      validate_folder_name("Bad\\Folder")

  def test_rejects_path_traversal_slash(self):
    """Test '..' in slash-separated paths is rejected."""
    with pytest.raises(ValueError, match="Invalid folder name"):
      validate_folder_name("foo/../bar")

  def test_rejects_path_traversal_dot(self):
    """Test '..' in dot-separated paths is rejected."""
    with pytest.raises(ValueError, match="Invalid folder name"):
      validate_folder_name("foo..bar")

  def test_rejects_leading_slash(self):
    """Test leading slash is rejected."""
    with pytest.raises(ValueError, match="Invalid folder name"):
      validate_folder_name("/Absolute")

  def test_rejects_leading_dot(self):
    """Test leading dot is rejected."""
    with pytest.raises(ValueError, match="Invalid folder name"):
      validate_folder_name(".Absolute")

  def test_rejects_deep_nesting_slash(self):
    """Test more than 10 slash levels is rejected."""
    deep_name = "/".join([f"level{i}" for i in range(11)])
    with pytest.raises(ValueError, match="exceeds maximum depth"):
      validate_folder_name(deep_name)

  def test_rejects_deep_nesting_dot(self):
    """Test more than 10 dot levels is rejected."""
    deep_dot = ".".join([f"level{i}" for i in range(11)])
    with pytest.raises(ValueError, match="exceeds maximum depth"):
      validate_folder_name(deep_dot)

  def test_rejects_inbox_uppercase(self):
    """Test INBOX is rejected."""
    with pytest.raises(ValueError, match="reserved folder name"):
      validate_folder_name("INBOX")

  def test_rejects_inbox_lowercase(self):
    """Test lowercase inbox is rejected."""
    with pytest.raises(ValueError, match="reserved folder name"):
      validate_folder_name("inbox")

  def test_rejects_inbox_mixed_case(self):
    """Test mixed case Inbox is rejected."""
    with pytest.raises(ValueError, match="reserved folder name"):
      validate_folder_name("Inbox")


class TestValidateAppendFlags:
  """Tests for validate_append_flags helper."""

  def test_empty_flags_returns_empty_list(self):
    """Test None flags return empty list."""
    result = validate_append_flags(None)
    assert result == []

  def test_valid_seen_flag(self):
    """Test \\Seen flag passes validation."""
    result = validate_append_flags(["\\Seen"])
    assert result == ["\\Seen"]

  def test_valid_multiple_flags(self):
    """Test multiple allowlisted flags pass validation."""
    result = validate_append_flags(["\\Seen", "\\Draft"])
    assert result == ["\\Seen", "\\Draft"]

  def test_rejects_invalid_flag(self):
    """Test flag outside allowlist is rejected."""
    with pytest.raises(ValueError, match="Invalid IMAP flag"):
      validate_append_flags(["\\Deleted"])

  def test_rejects_mixed_invalid_flag(self):
    """Test a mix of valid and invalid flags is rejected."""
    with pytest.raises(ValueError, match="Invalid IMAP flag"):
      validate_append_flags(["\\Seen", "\\Evil"])


class TestGetAppendMaxSize:
  """Tests for get_append_max_size helper."""

  def test_default_size(self, monkeypatch):
    """Default maximum size is 25 MB when no env override is set."""
    monkeypatch.delenv("EMAIL_APPEND_MAX_SIZE", raising=False)
    assert get_append_max_size() == APPEND_MAX_SIZE_DEFAULT

  def test_valid_env_override(self, monkeypatch):
    """Valid integer env value overrides the default."""
    monkeypatch.setenv("EMAIL_APPEND_MAX_SIZE", "1000")
    assert get_append_max_size() == 1000

  def test_invalid_env_fallback_to_default(self, monkeypatch):
    """Non-integer env value falls back to the default size."""
    monkeypatch.setenv("EMAIL_APPEND_MAX_SIZE", "not-a-number")
    assert get_append_max_size() == APPEND_MAX_SIZE_DEFAULT
