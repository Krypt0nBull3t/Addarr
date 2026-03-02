"""Tests for src/utils/splash.py"""

from unittest.mock import patch

from src.utils.splash import (
    get_splash_screen,
    show_splash_screen,
    show_version,
    show_welcome_screen,
    show_token_help,
)


# ---- get_splash_screen ----


class TestGetSplashScreen:
    """Tests for get_splash_screen -- returns formatted ASCII art string."""

    def test_returns_non_empty_string(self):
        """Splash screen returns a non-empty string."""
        result = get_splash_screen()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_refresh_edition(self):
        """Splash screen contains the REFRESH EDITION branding."""
        result = get_splash_screen()
        assert "REFRESH EDITION" in result

    def test_contains_addarr_ascii_art(self):
        """Splash screen contains the ADDARR ASCII art block letters."""
        result = get_splash_screen()
        # The ASCII art spells out ADDARR with block characters
        assert "█▀▀█" in result

    def test_contains_feature_tagline(self):
        """Splash screen includes the feature tagline icons."""
        result = get_splash_screen()
        assert "Organize" in result
        assert "Search" in result
        assert "Download" in result
        assert "Notify" in result


# ---- show_splash_screen ----


class TestShowSplashScreen:
    """Tests for show_splash_screen -- prints splash to stdout."""

    def test_prints_splash_to_stdout(self, capsys):
        """show_splash_screen writes the splash to stdout."""
        show_splash_screen()
        captured = capsys.readouterr()
        assert "REFRESH EDITION" in captured.out

    def test_output_is_non_empty(self, capsys):
        """show_splash_screen produces non-empty output."""
        show_splash_screen()
        captured = capsys.readouterr()
        assert len(captured.out) > 0


# ---- show_version ----


class TestShowVersion:
    """Tests for show_version -- prints version info to stdout."""

    def test_shows_version_number(self, capsys):
        """Output includes the version string."""
        show_version()
        captured = capsys.readouterr()
        assert "1.0.0" in captured.out

    def test_shows_addarr_label(self, capsys):
        """Output includes the Addarr Version label."""
        show_version()
        captured = capsys.readouterr()
        assert "Addarr Version" in captured.out

    def test_shows_repository_url(self, capsys):
        """Output includes the GitHub repository URL."""
        show_version()
        captured = capsys.readouterr()
        assert "https://github.com/cyneric/addarr" in captured.out

    def test_shows_documentation_url(self, capsys):
        """Output includes the wiki documentation URL."""
        show_version()
        captured = capsys.readouterr()
        assert "https://github.com/cyneric/addarr/wiki" in captured.out

    def test_shows_media_description(self, capsys):
        """Output includes the media management tagline."""
        show_version()
        captured = capsys.readouterr()
        assert "Telegram bot for media management" in captured.out


# ---- show_welcome_screen ----


class TestShowWelcomeScreen:
    """Tests for show_welcome_screen -- prints system info, config, and commands."""

    def test_shows_bot_header(self, capsys):
        """Output includes the Addarr Bot header."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Addarr Bot" in captured.out

    @patch("src.utils.splash.platform.python_version", return_value="3.11.5")
    def test_shows_python_version(self, mock_ver, capsys):
        """Output includes the Python version."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "3.11.5" in captured.out

    @patch("src.utils.splash.platform.platform", return_value="Linux-6.1-x86_64")
    def test_shows_os_info(self, mock_plat, capsys):
        """Output includes the OS platform string."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Linux-6.1-x86_64" in captured.out

    def test_debug_mode_disabled_by_default(self, capsys):
        """Default mock config has debug disabled -- shows disabled indicator."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Debug Mode" in captured.out
        assert "Disabled" in captured.out

    @patch("src.utils.splash.config")
    def test_debug_mode_enabled(self, mock_cfg, capsys):
        """When debug is True, output shows enabled indicator."""
        mock_cfg.get.side_effect = lambda key, default=None: {
            "logging": {"debug": True},
            "security": {"enableAdmin": False},
            "language": "en-us",
        }.get(key, default)

        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Debug Mode" in captured.out
        # Enabled indicator
        assert "Enabled" in captured.out

    def test_admin_mode_disabled_by_default(self, capsys):
        """Default mock config has admin disabled -- shows disabled indicator."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Admin Mode" in captured.out
        assert "Disabled" in captured.out

    @patch("src.utils.splash.config")
    def test_admin_mode_enabled(self, mock_cfg, capsys):
        """When enableAdmin is True, output shows enabled indicator."""
        mock_cfg.get.side_effect = lambda key, default=None: {
            "logging": {"debug": False},
            "security": {"enableAdmin": True},
            "language": "en-us",
        }.get(key, default)

        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Admin Mode" in captured.out
        # Both enabled and disabled will appear, check the admin line specifically
        lines = captured.out.split("\n")
        admin_line = [line for line in lines if "Admin Mode" in line][0]
        assert "Enabled" in admin_line

    def test_shows_default_language(self, capsys):
        """Default config shows en-us language."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "en-us" in captured.out

    @patch("src.utils.splash.config")
    def test_shows_custom_language(self, mock_cfg, capsys):
        """Custom language config is displayed."""
        mock_cfg.get.side_effect = lambda key, default=None: {
            "logging": {"debug": False},
            "security": {"enableAdmin": False},
            "language": "de-de",
        }.get(key, default)

        show_welcome_screen()
        captured = capsys.readouterr()
        assert "de-de" in captured.out

    def test_shows_cli_commands(self, capsys):
        """Output includes all CLI commands."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "python run.py" in captured.out
        assert "--setup" in captured.out
        assert "--configure" in captured.out
        assert "--check" in captured.out
        assert "--version" in captured.out
        assert "--backup" in captured.out
        assert "--reset" in captured.out
        assert "--validate-i18n" in captured.out
        assert "--help" in captured.out

    def test_shows_telegram_commands(self, capsys):
        """Output includes all Telegram chat commands."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "/movie" in captured.out
        assert "/series" in captured.out
        assert "/music" in captured.out
        assert "/delete" in captured.out
        assert "/status" in captured.out
        assert "/settings" in captured.out
        assert "/help" in captured.out

    def test_shows_resource_urls(self, capsys):
        """Output includes all resource URLs."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "https://github.com/cyneric/addarr" in captured.out
        assert "https://github.com/cyneric/addarr/wiki" in captured.out
        assert "https://github.com/cyneric/addarr/issues" in captured.out

    def test_shows_starting_message(self, capsys):
        """Output includes the starting bot message."""
        show_welcome_screen()
        captured = capsys.readouterr()
        assert "Starting bot" in captured.out


# ---- show_token_help ----


class TestShowTokenHelp:
    """Tests for show_token_help -- prints token configuration guidance."""

    def test_shows_invalid_token_header(self, capsys):
        """Output includes the invalid token error header."""
        show_token_help()
        captured = capsys.readouterr()
        assert "Invalid Telegram Bot Token" in captured.out

    def test_shows_botfather_instructions(self, capsys):
        """Output includes BotFather instructions."""
        show_token_help()
        captured = capsys.readouterr()
        assert "@BotFather" in captured.out
        assert "/newbot" in captured.out

    def test_shows_config_example(self, capsys):
        """Output includes config.yaml example."""
        show_token_help()
        captured = capsys.readouterr()
        assert "config.yaml" in captured.out
        assert "telegram" in captured.out
        assert "token" in captured.out

    def test_shows_setup_wizard_hint(self, capsys):
        """Output includes setup wizard command."""
        show_token_help()
        captured = capsys.readouterr()
        assert "python run.py --setup" in captured.out

    def test_shows_wiki_url(self, capsys):
        """Output includes the help wiki URL."""
        show_token_help()
        captured = capsys.readouterr()
        assert "https://github.com/cyneric/addarr/wiki" in captured.out
