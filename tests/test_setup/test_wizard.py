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


# ---------------------------------------------------------------------------
# Gap-fill: _update_config_value (line 66)
# ---------------------------------------------------------------------------


class TestUpdateConfigValue:
    """Tests for _update_config_value."""

    @patch("src.setup.wizard.config_handler")
    def test_delegates_to_config_handler(self, mock_handler):
        """_update_config_value calls config_handler.update_value."""
        mock_handler.load_config.return_value = {"key": "old"}

        wizard = SetupWizard()
        wizard._update_config_value(["key"], "new")

        mock_handler.update_value.assert_called_once_with(
            wizard.config, ["key"], "new"
        )


# ---------------------------------------------------------------------------
# Gap-fill: _create_directories (lines 128-134)
# ---------------------------------------------------------------------------


class TestCreateDirectories:
    """Tests for _create_directories."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.Path")
    @patch("src.setup.wizard.LOG_PATH", "/fake/logs/addarr.log")
    def test_creates_log_and_translations_dirs(self, mock_path, mock_handler):
        """Creates the log directory and translations directory."""
        mock_handler.load_config.return_value = {}

        wizard = SetupWizard()
        wizard._create_directories()

        # Should create two directories: log dir and translations
        assert mock_path.call_count == 2
        dir_args = [c.args[0] for c in mock_path.call_args_list]
        assert "/fake/logs" in dir_args
        assert "translations" in dir_args
        # Both should call mkdir with parents=True, exist_ok=True
        for call_obj in mock_path.return_value.mkdir.call_args_list:
            assert call_obj == (
                (), {"parents": True, "exist_ok": True}
            )


# ---------------------------------------------------------------------------
# Gap-fill: _configure_service (lines 138-159)
# ---------------------------------------------------------------------------


class TestConfigureService:
    """Tests for _configure_service."""

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.get_default_service_config")
    @patch("src.setup.wizard.get_valid_service_config", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_arr_features", new_callable=AsyncMock)
    async def test_arr_service_with_features(
        self, mock_features, mock_valid, mock_default, mock_handler
    ):
        """Arr services (radarr/sonarr/lidarr) get features configured."""
        mock_handler.load_config.return_value = {}
        mock_default.return_value = {"enable": False}
        mock_valid.return_value = {
            "server": {"addr": "localhost"},
            "auth": {"apikey": "key"},
        }
        mock_features.return_value = {"search": True}

        wizard = SetupWizard()
        await wizard._configure_service("radarr")

        mock_valid.assert_awaited_once_with("radarr")
        mock_features.assert_awaited_once_with("radarr")
        assert wizard.config["radarr"]["enable"] is True
        assert wizard.config["radarr"]["features"] == {"search": True}

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.get_default_service_config")
    @patch("src.setup.wizard.get_valid_service_config", new_callable=AsyncMock)
    @patch("src.setup.wizard.configure_arr_features", new_callable=AsyncMock)
    async def test_non_arr_service_no_features(
        self, mock_features, mock_valid, mock_default, mock_handler
    ):
        """Non-arr services (transmission) skip features configuration."""
        mock_handler.load_config.return_value = {}
        mock_default.return_value = {"enable": False}
        mock_valid.return_value = {"host": "localhost", "port": 9091}

        wizard = SetupWizard()
        await wizard._configure_service("transmission")

        mock_valid.assert_awaited_once_with("transmission")
        mock_features.assert_not_awaited()
        assert wizard.config["transmission"]["enable"] is True

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.get_default_service_config")
    @patch("src.setup.wizard.get_valid_service_config", new_callable=AsyncMock)
    async def test_exception_disables_service(
        self, mock_valid, mock_default, mock_handler, capsys
    ):
        """Exception during config sets enable=False."""
        mock_handler.load_config.return_value = {}
        mock_default.return_value = {"enable": False}
        mock_valid.side_effect = Exception("connection failed")

        wizard = SetupWizard()
        await wizard._configure_service("radarr")

        assert wizard.config["radarr"]["enable"] is False
        captured = capsys.readouterr()
        assert "Error configuring radarr" in captured.out


# ---------------------------------------------------------------------------
# Gap-fill: _configure_required_value (lines 163-168)
# ---------------------------------------------------------------------------


class TestConfigureRequiredValue:
    """Tests for _configure_required_value."""

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.configure_required_value", new_callable=AsyncMock)
    @patch("src.setup.wizard.get_default_service_config")
    async def test_arr_service_passes_default_config(
        self, mock_default, mock_crv, mock_handler
    ):
        """Arr services pass default_config to configure_required_value."""
        mock_handler.load_config.return_value = {}
        mock_default.return_value = {"server": {"addr": "localhost"}}
        mock_crv.return_value = {"radarr": {"updated": True}}

        wizard = SetupWizard()
        await wizard._configure_required_value("radarr", "apikey")

        mock_default.assert_called_once_with("radarr")
        # First arg is wizard.config at call time ({}), not return value
        mock_crv.assert_awaited_once()
        call_args = mock_crv.call_args
        assert call_args.args[1] == "radarr"
        assert call_args.args[2] == "apikey"
        assert call_args.kwargs["default_config"] == {
            "server": {"addr": "localhost"}
        }
        # Return value is assigned to wizard.config
        assert wizard.config == {"radarr": {"updated": True}}

    @pytest.mark.asyncio
    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.configure_required_value", new_callable=AsyncMock)
    async def test_non_arr_service_passes_none(self, mock_crv, mock_handler):
        """Non-arr services pass default_config=None."""
        mock_handler.load_config.return_value = {}
        mock_crv.return_value = {"transmission": {"updated": True}}

        wizard = SetupWizard()
        await wizard._configure_required_value("transmission", "host")

        mock_crv.assert_awaited_once()
        call_args = mock_crv.call_args
        assert call_args.args[1] == "transmission"
        assert call_args.args[2] == "host"
        assert call_args.kwargs["default_config"] is None
        assert wizard.config == {"transmission": {"updated": True}}


# ---------------------------------------------------------------------------
# Gap-fill: _reset_config success path (lines 207-223)
# ---------------------------------------------------------------------------


class TestResetConfigSuccess:
    """Tests for _reset_config success and error paths."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.create_backup", return_value="/backup/config.yaml")
    @patch("src.setup.wizard.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=MagicMock)
    @patch("src.setup.wizard.yaml")
    def test_success_loads_example_saves_and_runs(
        self, mock_yaml, mock_open, mock_exists, mock_backup,
        mock_q, mock_handler
    ):
        """Success path: backup, load example, save, run()."""
        mock_handler.load_config.return_value = {}
        mock_handler.save_config = MagicMock()

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_q.confirm.return_value = mock_confirm
        mock_q.Style = MagicMock()

        mock_yaml.load.return_value = {"telegram": {"token": ""}}

        wizard = SetupWizard()
        # Mock run() to prevent recursive loop
        wizard.run = MagicMock()

        wizard._reset_config()

        mock_backup.assert_called_once()
        mock_yaml.load.assert_called_once()
        mock_handler.save_config.assert_called_once()
        wizard.run.assert_called_once()

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.create_backup", return_value="/backup/config.yaml")
    @patch("src.setup.wizard.os.path.exists", return_value=False)
    def test_missing_example_exits_one(
        self, mock_exists, mock_backup, mock_q, mock_handler
    ):
        """Exits with code 1 when config_example.yaml not found."""
        mock_handler.load_config.return_value = {}

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_q.confirm.return_value = mock_confirm
        mock_q.Style = MagicMock()

        wizard = SetupWizard()

        with pytest.raises(SystemExit) as exc_info:
            wizard._reset_config()

        assert exc_info.value.code == 1

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.create_backup", return_value="/backup/config.yaml")
    @patch("src.setup.wizard.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=Exception("read error"))
    def test_exception_exits_one(
        self, mock_open, mock_exists, mock_backup,
        mock_q, mock_handler
    ):
        """Generic exception during reset calls sys.exit(1)."""
        mock_handler.load_config.return_value = {}

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True
        mock_q.confirm.return_value = mock_confirm
        mock_q.Style = MagicMock()

        wizard = SetupWizard()

        with pytest.raises(SystemExit) as exc_info:
            wizard._reset_config()

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Gap-fill: configure_services Transmission auth + SABnzbd (lines 259-279)
# ---------------------------------------------------------------------------


class TestConfigureServicesGapFill:
    """Gap-fill tests for Transmission auth and SABnzbd paths."""

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.questionary")
    def test_transmission_with_auth(self, mock_q, mock_splash, mock_handler):
        """Transmission auth configures username and password."""
        mock_handler.load_config.return_value = {}
        mock_handler.save_config = MagicMock()

        # Sequence: radarr=No, sonarr=No, lidarr=No,
        # transmission=Yes, auth=Yes, sabnzbd=No
        confirm_mock = MagicMock()
        confirm_mock.ask.side_effect = [
            False, False, False,  # skip media services
            True,   # configure transmission
            True,   # enable auth
            False,  # skip sabnzbd
        ]
        mock_q.confirm.return_value = confirm_mock

        # Username and password prompts
        text_mock = MagicMock()
        text_mock.ask.return_value = "admin"
        mock_q.text.return_value = text_mock

        password_mock = MagicMock()
        password_mock.ask.return_value = "secret123"
        mock_q.password.return_value = password_mock

        wizard = SetupWizard()
        wizard.configure_services()

        assert wizard.config["transmission"]["enable"] is True
        assert wizard.config["transmission"]["authentication"] is True
        assert wizard.config["transmission"]["username"] == "admin"
        assert wizard.config["transmission"]["password"] == "secret123"

    @patch("src.setup.wizard.config_handler")
    @patch("src.setup.wizard.show_splash_screen")
    @patch("src.setup.wizard.questionary")
    @patch("src.setup.wizard.asyncio")
    def test_sabnzbd_config(self, mock_asyncio, mock_q, mock_splash, mock_handler):
        """SABnzbd configuration gets valid config via asyncio.run."""
        mock_handler.load_config.return_value = {}
        mock_handler.save_config = MagicMock()

        # Sequence: radarr=No, sonarr=No, lidarr=No,
        # transmission=No, sabnzbd=Yes
        confirm_mock = MagicMock()
        confirm_mock.ask.side_effect = [
            False, False, False,  # skip media services
            False,  # skip transmission
            True,   # configure sabnzbd
        ]
        mock_q.confirm.return_value = confirm_mock

        mock_asyncio.run.return_value = {
            "server": {"addr": "localhost", "port": 8090},
            "auth": {"apikey": "sab-key"},
        }

        wizard = SetupWizard()
        wizard.configure_services()

        mock_asyncio.run.assert_called_once()
        assert wizard.config["sabnzbd"]["enable"] is True
        assert wizard.config["sabnzbd"]["auth"]["apikey"] == "sab-key"
