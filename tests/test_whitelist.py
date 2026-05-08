"""Tests for recipient whitelist."""

from simple_email_gw.config import RecipientWhitelist


class TestRecipientWhitelist:
  """Tests for RecipientWhitelist model."""

  def test_disabled_allows_all(self):
    """Test disabled whitelist allows all recipients."""
    whitelist = RecipientWhitelist(enabled=False, domains=[], addresses=[])

    assert whitelist.is_allowed("anyone@example.com") is True
    assert whitelist.is_allowed("external@external.com") is True

  def test_domain_whitelist(self):
    """Test domain-based whitelist."""
    whitelist = RecipientWhitelist(
      enabled=True,
      domains=["example.com", "trusted.org"],
      addresses=[],
    )

    assert whitelist.is_allowed("user@example.com") is True
    assert whitelist.is_allowed("admin@trusted.org") is True
    assert whitelist.is_allowed("external@other.com") is False

  def test_address_whitelist(self):
    """Test address-based whitelist."""
    whitelist = RecipientWhitelist(
      enabled=True,
      domains=[],
      addresses=["specific@external.com", "admin@company.org"],
    )

    assert whitelist.is_allowed("specific@external.com") is True
    assert whitelist.is_allowed("admin@company.org") is True
    assert whitelist.is_allowed("other@external.com") is False

  def test_combined_whitelist(self):
    """Test combined domain and address whitelist."""
    whitelist = RecipientWhitelist(
      enabled=True,
      domains=["example.com"],
      addresses=["specific@external.com"],
    )

    # Domain match
    assert whitelist.is_allowed("user@example.com") is True
    # Address match
    assert whitelist.is_allowed("specific@external.com") is True
    # Neither
    assert whitelist.is_allowed("other@external.com") is False

  def test_case_insensitive(self):
    """Test whitelist is case insensitive."""
    whitelist = RecipientWhitelist(
      enabled=True,
      domains=["Example.COM"],
      addresses=["User@External.COM"],
    )

    # Domain match (case insensitive)
    assert whitelist.is_allowed("user@example.com") is True
    assert whitelist.is_allowed("USER@EXAMPLE.COM") is True
    # Address match (case insensitive)
    assert whitelist.is_allowed("user@external.com") is True
    assert whitelist.is_allowed("USER@EXTERNAL.COM") is True
    # Neither domain nor address match
    assert whitelist.is_allowed("user@other.com") is False
    assert whitelist.is_allowed("random@unknown.org") is False

  def test_filter_recipients(self):
    """Test filtering recipient lists."""
    whitelist = RecipientWhitelist(
      enabled=True,
      domains=["trusted.com"],
      addresses=["specific@external.com"],
    )

    recipients = [
      "user@trusted.com",
      "admin@trusted.com",
      "specific@external.com",
      "blocked@other.com",
      "also@blocked.org",
    ]

    allowed, blocked = whitelist.filter_recipients(recipients)

    assert len(allowed) == 3
    assert "user@trusted.com" in allowed
    assert "admin@trusted.com" in allowed
    assert "specific@external.com" in allowed

    assert len(blocked) == 2
    assert "blocked@other.com" in blocked
    assert "also@blocked.org" in blocked
