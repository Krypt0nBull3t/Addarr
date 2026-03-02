"""Tests for src/utils/prerun.py"""

import json
import subprocess
from unittest.mock import MagicMock, patch

from src.utils.prerun import ColorHandler, PreRunChecker, prerun_checker


# ---- DummyFore / DummyStyle ----


class TestDummyClasses:
    """Tests for DummyFore and DummyStyle fallback classes."""

    def test_dummy_fore_attributes_are_empty_strings(self):
        """DummyFore.RED/GREEN/YELLOW/CYAN are all empty strings."""
        dummy = ColorHandler.DummyFore()
        assert dummy.RED == ""
        assert dummy.GREEN == ""
        assert dummy.YELLOW == ""
        assert dummy.CYAN == ""

    def test_dummy_style_reset_all_is_empty_string(self):
        """DummyStyle.RESET_ALL is an empty string."""
        dummy = ColorHandler.DummyStyle()
        assert dummy.RESET_ALL == ""


# ---- ColorHandler.__init__ ----


class TestColorHandlerInit:
    """Tests for ColorHandler initialization."""

    def test_with_colorama_available(self):
        """When colorama is importable, Fore/Style are real colorama objects."""
        handler = ColorHandler()
        # colorama is installed in test env
        from colorama import Fore, Style
        assert handler.Fore is Fore
        assert handler.Style is Style

    def test_with_colorama_import_error(self):
        """When colorama import fails, falls back to DummyFore/DummyStyle."""
        with patch.dict("sys.modules", {"colorama": None}):
            handler = ColorHandler()
        assert isinstance(handler.Fore, ColorHandler.DummyFore)
        assert isinstance(handler.Style, ColorHandler.DummyStyle)


# ---- ColorHandler.reload ----


class TestColorHandlerReload:
    """Tests for ColorHandler.reload."""

    def test_reload_with_colorama(self):
        """Successful reload updates Fore/Style."""
        handler = ColorHandler()
        handler.Fore = None  # clobber
        handler.reload()
        from colorama import Fore
        assert handler.Fore is Fore

    def test_reload_with_import_error(self):
        """ImportError during reload is a no-op (Fore/Style unchanged)."""
        handler = ColorHandler()
        original_fore = handler.Fore
        with patch.dict("sys.modules", {"colorama": None}):
            handler.reload()
        # Fore should be unchanged
        assert handler.Fore is original_fore


# ---- PreRunChecker.__init__ ----


class TestPreRunCheckerInit:
    """Tests for PreRunChecker initialization."""

    def test_colors_is_color_handler(self):
        """colors attribute is a ColorHandler instance."""
        checker = PreRunChecker()
        assert isinstance(checker.colors, ColorHandler)

    def test_root_dir_is_absolute(self):
        """root_dir is an absolute path."""
        checker = PreRunChecker()
        import os
        assert os.path.isabs(checker.root_dir)

    def test_config_path_ends_with_config_yaml(self):
        """config_path ends with config.yaml."""
        checker = PreRunChecker()
        assert checker.config_path.endswith("config.yaml")


# ---- parse_requirements ----


class TestParseRequirements:
    """Tests for parse_requirements."""

    def test_reads_packages_from_file(self, tmp_path):
        """Parses package names from requirements file."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests\naiohttp\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert "requests" in result
        assert "aiohttp" in result

    def test_strips_version_specifiers(self, tmp_path):
        """Strips >=, <=, == version specifiers."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            "requests>=2.28.0\naiohttp<=3.9.0\nflask==2.3.0\n"
        )
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert "requests" in result
        assert "aiohttp" in result
        assert "flask" in result
        # No version strings
        assert not any(">=" in p for p in result)
        assert not any("<=" in p for p in result)
        assert not any("==" in p for p in result)

    def test_strips_inline_comments(self, tmp_path):
        """Strips inline # comments from lines."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests  # HTTP library\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert "requests" in result
        assert not any("#" in p for p in result)

    def test_skips_comment_lines(self, tmp_path):
        """Lines starting with # are skipped entirely."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# This is a comment\nrequests\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert "requests" in result
        assert len([p for p in result if p.startswith("#")]) == 0

    def test_skips_blank_lines(self, tmp_path):
        """Empty lines are skipped."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests\n\n\naiohttp\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert "requests" in result
        assert "aiohttp" in result

    def test_lowercases_package_names(self, tmp_path):
        """Package names are lowercased."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("Flask\nDjango\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert "flask" in result
        assert "django" in result

    def test_file_not_found_returns_core_deps(self, capsys):
        """FileNotFoundError returns core_deps list."""
        checker = PreRunChecker()
        result = checker.parse_requirements("/nonexistent/requirements.txt")
        assert "colorama" in result
        assert "python-telegram-bot" in result
        assert "pyyaml" in result
        assert "ruamel.yaml" in result
        captured = capsys.readouterr()
        assert "requirements.txt not found" in captured.out

    def test_merges_with_core_deps(self, tmp_path):
        """Result includes both file packages and core deps."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("custom-package\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        # File package
        assert "custom-package" in result
        # Core deps
        assert "colorama" in result
        assert "python-telegram-bot" in result

    def test_deduplicates(self, tmp_path):
        """Duplicate packages between file and core_deps are deduplicated."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("colorama\npyyaml\n")
        checker = PreRunChecker()
        result = checker.parse_requirements(str(req_file))
        assert result.count("colorama") == 1
        assert result.count("pyyaml") == 1


# ---- get_installed_packages ----


class TestGetInstalledPackages:
    """Tests for get_installed_packages."""

    @patch("src.utils.prerun.subprocess.run")
    def test_parses_json_output(self, mock_run):
        """Parses pip list JSON and returns package names."""
        mock_run.return_value.stdout = json.dumps([
            {"name": "requests", "version": "2.28.0"},
            {"name": "aiohttp", "version": "3.9.0"},
        ])
        checker = PreRunChecker()
        result = checker.get_installed_packages()
        assert "requests" in result
        assert "aiohttp" in result

    @patch("src.utils.prerun.subprocess.run")
    def test_normalizes_hyphen_underscore(self, mock_run):
        """Adds both hyphen and underscore variants."""
        mock_run.return_value.stdout = json.dumps([
            {"name": "python-telegram-bot", "version": "20.0"},
        ])
        checker = PreRunChecker()
        result = checker.get_installed_packages()
        assert "python-telegram-bot" in result
        assert "python_telegram_bot" in result

    @patch("src.utils.prerun.subprocess.run")
    def test_lowercases_names(self, mock_run):
        """Package names are lowercased."""
        mock_run.return_value.stdout = json.dumps([
            {"name": "Flask", "version": "2.3.0"},
        ])
        checker = PreRunChecker()
        result = checker.get_installed_packages()
        assert "flask" in result

    @patch("src.utils.prerun.subprocess.run")
    def test_subprocess_error_returns_empty_set(self, mock_run, capsys):
        """Returns empty set on subprocess failure."""
        mock_run.side_effect = Exception("pip failed")
        checker = PreRunChecker()
        result = checker.get_installed_packages()
        assert result == set()
        captured = capsys.readouterr()
        assert "Error getting installed packages" in captured.out


# ---- check_dependencies ----


class TestCheckDependencies:
    """Tests for check_dependencies."""

    def test_all_installed_returns_true(self):
        """Returns True when all packages are installed."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=["requests"])
        checker.get_installed_packages = MagicMock(
            return_value={"requests"}
        )
        assert checker.check_dependencies() is True

    def test_empty_requirements_returns_false(self, capsys):
        """Returns False when parse_requirements returns empty list."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=[])
        result = checker.check_dependencies()
        assert result is False
        captured = capsys.readouterr()
        assert "No dependencies found" in captured.out

    @patch("builtins.input", return_value="y")
    @patch("src.utils.prerun.subprocess.check_call")
    def test_missing_packages_install_yes(self, mock_install, mock_input):
        """Installs missing packages when user says yes."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=["missing-pkg"])
        checker.get_installed_packages = MagicMock(return_value=set())
        result = checker.check_dependencies()
        assert result is True
        mock_install.assert_called_once()

    @patch("builtins.input", return_value="n")
    def test_missing_packages_decline(self, mock_input, capsys):
        """Returns False when user declines to install."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=["missing-pkg"])
        checker.get_installed_packages = MagicMock(return_value=set())
        result = checker.check_dependencies()
        assert result is False
        captured = capsys.readouterr()
        assert "Cannot continue without required dependencies" in captured.out

    @patch("builtins.input", return_value="y")
    @patch("src.utils.prerun.subprocess.check_call",
           side_effect=subprocess.CalledProcessError(1, "pip"))
    def test_install_failure(self, mock_install, mock_input, capsys):
        """Returns False when pip install fails."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=["missing-pkg"])
        checker.get_installed_packages = MagicMock(return_value=set())
        result = checker.check_dependencies()
        assert result is False
        captured = capsys.readouterr()
        assert "Failed to install dependencies" in captured.out

    @patch("builtins.input", return_value="y")
    @patch("src.utils.prerun.subprocess.check_call")
    def test_colorama_reload_triggered(self, mock_install, mock_input):
        """Reloads colorama when it was among the missing packages."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=["colorama"])
        checker.get_installed_packages = MagicMock(return_value=set())
        checker.colors.reload = MagicMock()
        result = checker.check_dependencies()
        assert result is True
        checker.colors.reload.assert_called_once()

    @patch("builtins.input", side_effect=["invalid", "x", "n"])
    def test_invalid_input_loop(self, mock_input, capsys):
        """Loops on invalid input until valid y/n is given."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(return_value=["missing-pkg"])
        checker.get_installed_packages = MagicMock(return_value=set())
        result = checker.check_dependencies()
        assert result is False
        captured = capsys.readouterr()
        assert captured.out.count("Please answer with 'y' or 'n'") == 2

    def test_hyphen_underscore_matching(self):
        """Packages match despite hyphen/underscore differences."""
        checker = PreRunChecker()
        checker.parse_requirements = MagicMock(
            return_value=["python-telegram-bot"]
        )
        checker.get_installed_packages = MagicMock(
            return_value={"python_telegram_bot"}
        )
        assert checker.check_dependencies() is True


# ---- check_config_exists ----


class TestCheckConfigExists:
    """Tests for check_config_exists."""

    @patch("os.path.exists", return_value=True)
    def test_config_exists_returns_true(self, mock_exists):
        """Returns True when config.yaml exists."""
        checker = PreRunChecker()
        with patch("src.utils.config_handler.config_handler"):
            result = checker.check_config_exists()
        assert result is True

    @patch("os.path.exists", return_value=True)
    def test_sets_config_handler_colors(self, mock_exists):
        """Sets config_handler.colors to checker's colors."""
        checker = PreRunChecker()
        with patch(
            "src.utils.config_handler.config_handler"
        ) as mock_ch:
            checker.check_config_exists()
        assert mock_ch.colors is checker.colors

    @patch("os.path.exists", return_value=False)
    @patch("builtins.input", return_value="y")
    def test_missing_config_runs_wizard(self, mock_input, mock_exists):
        """Runs SetupWizard when user says yes to setup."""
        checker = PreRunChecker()
        mock_ch = MagicMock()
        mock_ch.create_from_example.return_value = True
        mock_wizard_cls = MagicMock()

        with (
            patch(
                "src.utils.config_handler.config_handler", mock_ch
            ),
            patch("src.setup.SetupWizard", mock_wizard_cls),
        ):
            result = checker.check_config_exists()

        assert result is True
        mock_ch.create_from_example.assert_called_once()
        mock_wizard_cls.return_value.run.assert_called_once()

    @patch("os.path.exists", return_value=False)
    @patch("builtins.input", return_value="y")
    def test_create_from_example_fails(self, mock_input, mock_exists):
        """Returns False when create_from_example fails."""
        checker = PreRunChecker()
        mock_ch = MagicMock()
        mock_ch.create_from_example.return_value = False

        with patch(
            "src.utils.config_handler.config_handler", mock_ch
        ):
            result = checker.check_config_exists()

        assert result is False

    @patch("os.path.exists", return_value=False)
    @patch("builtins.input", return_value="n")
    def test_decline_setup_returns_false(self, mock_input, mock_exists, capsys):
        """Returns False when user declines setup."""
        checker = PreRunChecker()
        with patch(
            "src.utils.config_handler.config_handler"
        ):
            result = checker.check_config_exists()
        assert result is False
        captured = capsys.readouterr()
        assert "Cannot continue without configuration" in captured.out

    @patch("os.path.exists", return_value=False)
    @patch("builtins.input", side_effect=["maybe", "n"])
    def test_invalid_input_loop(self, mock_input, mock_exists, capsys):
        """Loops on invalid input, then accepts valid response."""
        checker = PreRunChecker()
        with patch(
            "src.utils.config_handler.config_handler"
        ):
            result = checker.check_config_exists()
        assert result is False
        captured = capsys.readouterr()
        assert "Please answer with 'y' or 'n'" in captured.out


# ---- run_checks ----


class TestRunChecks:
    """Tests for run_checks."""

    def test_both_pass(self):
        """Returns True when both dependencies and config checks pass."""
        checker = PreRunChecker()
        checker.check_dependencies = MagicMock(return_value=True)
        checker.check_config_exists = MagicMock(return_value=True)
        assert checker.run_checks() is True
        checker.check_dependencies.assert_called_once()
        checker.check_config_exists.assert_called_once()

    def test_deps_fail_skips_config(self):
        """Returns False and skips config check when deps fail."""
        checker = PreRunChecker()
        checker.check_dependencies = MagicMock(return_value=False)
        checker.check_config_exists = MagicMock()
        assert checker.run_checks() is False
        checker.check_config_exists.assert_not_called()

    def test_config_fail(self):
        """Returns False when config check fails."""
        checker = PreRunChecker()
        checker.check_dependencies = MagicMock(return_value=True)
        checker.check_config_exists = MagicMock(return_value=False)
        assert checker.run_checks() is False


# ---- global prerun_checker instance ----


class TestGlobalInstance:
    """Tests for the module-level prerun_checker."""

    def test_is_prerun_checker_instance(self):
        """Global instance is a PreRunChecker."""
        assert isinstance(prerun_checker, PreRunChecker)

    def test_has_colors(self):
        """Global instance has a ColorHandler."""
        assert isinstance(prerun_checker.colors, ColorHandler)
