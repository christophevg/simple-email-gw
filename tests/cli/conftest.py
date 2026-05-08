"""Pytest configuration for CLI tests.

Sets up the theme to DARK before each test so tests expect bright colors
that work well on dark backgrounds.
"""

import pytest

from simple_email_gw.cli.theme import ThemeType, get_theme_manager


@pytest.fixture(autouse=True)
def set_dark_theme():
  """Set theme to DARK before each test.

  This ensures tests expect bright colors that work well on dark backgrounds,
  which matches the original test expectations.
  """
  theme_manager = get_theme_manager()
  theme_manager.set_theme(ThemeType.DARK)
  yield
  # Reset to LIGHT theme (default) after test
  theme_manager.set_theme(ThemeType.LIGHT)
