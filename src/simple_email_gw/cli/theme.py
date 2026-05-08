"""
Theme management for CLI output.

This module provides theme-aware color schemes for both light and dark
terminal backgrounds, ensuring good readability across different terminal themes.
"""

from enum import Enum


class ThemeType(Enum):
  """Available theme types."""

  LIGHT = "light"
  DARK = "dark"


class ColorTheme:
  """Color theme with colors optimized for readability on different backgrounds."""

  def __init__(self, theme_type: ThemeType):
    """Initialize theme with specified type.

    Args:
        theme_type: LIGHT or DARK theme type
    """
    self.theme_type = theme_type

    if theme_type == ThemeType.LIGHT:
      # Colors for light/white backgrounds - use darker colors for contrast
      self.account_name = "dark_blue"
      self.folder_name = "dark_green"
      self.email_id = "dark_blue"
      self.email_subject = "black"
      self.email_subject_unread = "bold ansiblue"
      self.unread_indicator = "bold ansiblue"
      self.date = "black"
      self.error = "dark_red"
      self.error_border = "dark_red"
      self.success = "dark_green"
      self.success_border = "dark_green"
      self.warning = "dark_orange3"
      self.warning_border = "dark_orange3"
      self.secondary = "grey50"  # Darker than dim, better contrast
      self.prompt_account = "ansiblue"
      self.prompt_folder = "ansigreen"
    else:  # DARK
      # Colors for dark/black backgrounds - use bright colors for contrast
      self.account_name = "cyan"
      self.folder_name = "green"
      self.email_id = "cyan"
      self.email_subject = "white"
      self.email_subject_unread = "bold ansicyan"
      self.unread_indicator = "bold ansicyan"
      self.date = "white"
      self.error = "red"
      self.error_border = "red"
      self.success = "green"
      self.success_border = "green"
      self.warning = "yellow"
      self.warning_border = "yellow"
      self.secondary = "dim"  # Standard dim works well on dark
      self.prompt_account = "ansicyan"
      self.prompt_folder = "ansigreen"


# Global theme manager singleton
class ThemeManager:
  """Global theme manager for CLI."""

  _instance = None
  _current_theme: ColorTheme

  def __new__(cls) -> "ThemeManager":
    """Create singleton instance."""
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      # Default to LIGHT theme for better safety (dark text on light bg works better than light on dark)
      cls._current_theme = ColorTheme(ThemeType.LIGHT)
    return cls._instance

  @property
  def theme(self) -> ColorTheme:
    """Get current theme."""
    return self._current_theme

  def set_theme(self, theme_type: ThemeType) -> None:
    """Set theme type.

    Args:
        theme_type: LIGHT or DARK theme type
    """
    self._current_theme = ColorTheme(theme_type)

  def toggle_theme(self) -> ThemeType:
    """Toggle between light and dark themes.

    Returns:
        New theme type after toggle
    """
    if self._current_theme.theme_type == ThemeType.LIGHT:
      new_type = ThemeType.DARK
    else:
      new_type = ThemeType.LIGHT

    self.set_theme(new_type)
    return new_type

  def get_theme_type(self) -> ThemeType:
    """Get current theme type."""
    return self._current_theme.theme_type


def get_theme_manager() -> ThemeManager:
  """Get the global theme manager instance."""
  return ThemeManager()
