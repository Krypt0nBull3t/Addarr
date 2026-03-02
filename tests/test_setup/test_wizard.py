"""Tests for src.setup.wizard module — orchestration logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.setup.wizard import SetupWizard, main


# ---------------------------------------------------------------------------
# SetupWizard.__init__ tests
# ---------------------------------------------------------------------------


class TestWizardInit:
    """Tests for SetupWizard initialization."""

    @patch("src.setup.wizard.config_handler")
    def test_loads_config_on_init(self, mock_handler):
        """__init__ calls config_handler.load_config and stores result."""
        mock_handler.load_config.return_value = {"language": "en-us"}

        wizard = SetupWizard()

        mock_handler.load_config.assert_called_once()
        assert wizard.config == {"language": "en-us"}

    @patch("src.setup.wizard.config_handler")
    def test_sets_root_dir(self, mock_handler):
        """__init__ sets root_dir three levels above wizard.py."""
        mock_handler.load_config.return_value = {}

        wizard = SetupWizard()

        # root_dir should be a string path and exist (it's the repo root)
        assert isinstance(wizard.root_dir, str)
        assert len(wizard.root_dir) > 0


# ---------------------------------------------------------------------------
# SetupWizard.run tests
# ---------------------------------------------------------------------------


class TestWizardRun:
    """Tests for SetupWizard.run() orchestration."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.asyncio")
    def test_run_creates_loop_and_calls_async_setup(
        self, mock_asyncio, mock_splash, mock_handler
    ):
        """run() creates event loop and calls _async_setup via run_until_complete."""
        mock_handler.load_config.return_value = {}
        # Simulate no running loop (RuntimeError) -> create new one
        mock_asyncio.get_running_loop.side_effect = RuntimeError
        mock_loop = MagicMock()
        mock_asyncio.new_event_loop.return_value = mock_loop

        wizard = SetupWizard()
        wizard._create_directories = MagicMock()
        wizard.run()

        mock_splash.assert_called_once()
        mock_asyncio.new_event_loop.assert_called_once()
        mock_asyncio.set_event_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.asyncio")
    def test_run_with_reset_calls_reset_config(
        self, mock_asyncio, mock_splash, mock_handler
    ):
        """run(reset=True) calls _reset_config before async setup."""
        mock_handler.load_config.return_value = {}
        mock_asyncio.get_running_loop.side_effect = RuntimeError
        mock_loop = MagicMock()
        mock_asyncio.new_event_loop.return_value = mock_loop

        wizard = SetupWizard()
        wizard._create_directories = MagicMock()
        wizard._reset_config = MagicMock()
        wizard.run(reset=True)

        wizard._reset_config.assert_called_once()

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.asyncio")
    @patch("src.setup.wizard.sys")
    def test_run_exits_on_exception(
        self, mock_sys, mock_asyncio, mock_splash, mock_handler
    ):
        """run() calls sys.exit(1) if async setup raises."""
        mock_handler.load_config.return_value = {}
        mock_asyncio.get_running_loop.side_effect = RuntimeError
        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = Exception("setup failed")
        mock_asyncio.new_event_loop.return_value = mock_loop

        wizard = SetupWizard()
        wizard._create_directories = MagicMock()
        wizard.run()

        mock_sys.exit.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# SetupWizard._async_setup tests
# ---------------------------------------------------------------------------


class TestWizardAsyncSetup:
    """Tests for _async_setup() orchestration."""

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.configure_logging", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_access_control", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_telegram", new_callable=AsyncMock)
    @patch("src.setup.wizard.select_services", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_language", new_callable=AsyncMock)
    async def test_orchestration_calls_all_prompts(
        self,
        mock_language,
        mock_services,
        mock_telegram,
        mock_access,
        mock_logging,
        mock_handler,
    ):
        """_async_setup calls all prompt functions and assigns to config."""
        mock_handler.load_config.return_value = {}
        mock_handler.save_config = MagicMock()

        mock_language.return_value = "en-us"
        mock_services.return_value = ["radarr"]
        mock_telegram.return_value = {"token": "abc", "password": "xyz"}
        mock_access.return_value = {
            "security": {"enableAdmin": True},
            "admins": [111],
        }
        mock_logging.return_value = {"toConsole": True, "debug": False}

        wizard = SetupWizard()
        wizard._configure_service = AsyncMock()
        await wizard._async_setup()

        mock_language.assert_awaited_once()
        mock_services.assert_awaited_once()
        wizard._configure_service.assert_awaited_once_with("radarr")
        mock_telegram.assert_awaited_once()
        mock_access.assert_awaited_once()
        mock_logging.assert_awaited_once()

        assert wizard.config["language"] == "en-us"
        assert wizard.config["telegram"] == {"token": "abc", "password": "xyz"}
        assert wizard.config["security"] == {"enableAdmin": True}
        assert wizard.config["admins"] == [111]
        assert wizard.config["logging"] == {"toConsole": True, "debug": False}

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.configure_logging", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_access_control", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_telegram", new_callable=AsyncMock)
    @patch("src.setup.wizard.select_services", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_language", new_callable=AsyncMock)
    async def test_access_control_with_allow_list(
        self,
        mock_language,
        mock_services,
        mock_telegram,
        mock_access,
        mock_logging,
        mock_handler,
    ):
        """_async_setup unpacks allow_list when present in access config."""
        mock_handler.load_config.return_value = {}
        mock_handler.save_config = MagicMock()

        mock_language.return_value = "en-us"
        mock_services.return_value = []
        mock_telegram.return_value = {"token": "t", "password": "p"}
        mock_access.return_value = {
            "security": {"enableAllowlist": True},
            "admins": [111],
            "allow_list": [222],
        }
        mock_logging.return_value = {}

        wizard = SetupWizard()
        await wizard._async_setup()

        assert wizard.config["allow_list"] == [222]


# ---------------------------------------------------------------------------
# SetupWizard._reset_config tests
# ---------------------------------------------------------------------------


class TestWizardResetConfig:
    """Tests for _reset_config()."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.questionary")
    def test_cancelled_exits_zero(self, mock_q, mock_handler):
        """Declining reset confirmation calls sys.exit(0)."""
        mock_handler.load_config.return_value = {}

        # questionary.confirm(...).ask() returns False
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        mock_q.confirm.return_value = mock_confirm
        mock_q.Style = MagicMock()

        wizard = SetupWizard()

        with pytest.raises(SystemExit) as exc_info:
            wizard._reset_config()

        assert exc_info.value.code == 0

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.create_backup")
    def test_backup_failure_exits_one(self, mock_backup, mock_q, mock_handler):
        """Failed backup calls sys.exit(1)."""
        mock_handler.load_config.return_value = {}

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_q.confirm.return_value = mock_confirm
        mock_q.Style = MagicMock()
        mock_backup.return_value = None  # backup failed

        wizard = SetupWizard()

        with pytest.raises(SystemExit) as exc_info:
            wizard._reset_config()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# SetupWizard.configure_services tests
# ---------------------------------------------------------------------------


class TestWizardConfigureServices:
    """Tests for configure_services() sync method."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.asyncio")
    def test_configures_selected_service(
        self, mock_asyncio, mock_q, mock_splash, mock_handler
    ):
        """configure_services() configures a service the user selects."""
        mock_handler.load_config.return_value = {}
        mock_handler.save_config = MagicMock()

        # First 3 confirm calls (radarr=Yes, sonarr=No, lidarr=No),
        # then transmission=No, sabnzbd=No
        confirm_mock = MagicMock()
        confirm_mock.ask.side_effect = [True, False, False, False, False]
        mock_q.confirm.return_value = confirm_mock

        mock_asyncio.run.return_value = {
            "server": {"addr": "localhost", "port": 7878},
            "auth": {"apikey": "key123"},
        }

        wizard = SetupWizard()
        wizard.configure_services()

        # asyncio.run called for radarr's get_valid_service_config
        mock_asyncio.run.assert_called_once()
        assert wizard.config["radarr"]["enable"] is True
        mock_handler.save_config.assert_called_once()

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.sys")
    def test_exits_on_error(self, mock_sys, mock_q, mock_splash, mock_handler):
        """configure_services() calls sys.exit(1) on exception."""
        mock_handler.load_config.return_value = {}

        # Make questionary.confirm raise
        mock_q.confirm.side_effect = Exception("terminal error")

        wizard = SetupWizard()
        wizard.configure_services()

        mock_sys.exit.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() entry point."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.SetupWizard")
    @patch("src.setup.wizard.sys")
    def test_main_creates_wizard_and_runs(self, mock_sys, mock_cls, mock_handler):
        """main() creates a SetupWizard instance and calls run()."""
        mock_sys.argv = ["run.py", "--setup"]
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        main()

        mock_cls.assert_called_once()
        mock_instance.run.assert_called_once_with(False)

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.SetupWizard")
    @patch("src.setup.wizard.sys")
    def test_main_with_reset_flag(self, mock_sys, mock_cls, mock_handler):
        """main() passes reset=True when --reset in argv."""
        mock_sys.argv = ["run.py", "--reset"]
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        main()

        mock_instance.run.assert_called_once_with(True)
