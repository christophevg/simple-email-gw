"""Pytest configuration for CLI tests.

Sets up the theme to DARK before each test so tests expect bright colors
that work well on dark backgrounds.

Also patches prompt_toolkit's output factory on Windows to avoid
NoConsoleScreenBufferError on headless CI runners.
"""

import sys

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


@pytest.fixture(autouse=True)
def _dummy_prompt_toolkit_output(monkeypatch):
  """Use a DummyOutput on Windows to avoid needing a real console.

  GitHub Actions Windows runners are headless, so prompt_toolkit's default
  Win32Output raises NoConsoleScreenBufferError. This fixture is a no-op on
  non-Windows platforms.
  """
  if sys.platform != "win32":
    yield
    return

  from prompt_toolkit.output import DummyOutput

  monkeypatch.setattr(
    "prompt_toolkit.output.defaults.create_output", lambda *_args, **_kwargs: DummyOutput()
  )
  yield
