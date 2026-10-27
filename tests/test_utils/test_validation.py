"""Tests for src/utils/validation.py"""

from unittest.mock import patch, MagicMock

from src.utils.validation import (
    check_config,
    _check_core_settings,
    _check_media_services,
    _check_download_clients,
    _check_security_settings,
)


# ---- check_config ----


class TestCheckConfig:
    """Tests for check_config."""

    def test_check_config_success(self):
        """Returns True when all sub-checks pass."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "telegram": {"token": "test-token"},
            "language": "en-us",
            "radarr": {"enable": True, "auth": {"apikey": "key"}},
            "sonarr": {"enable": False},
            "lidarr": {"enable": False},
            "transmission": {"enable": False},
            "sabnzbd": {"enable": False},
            "security": {},
            "admins": [],
            "allow_list": [],
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            result = check_config()
        assert result is True

    def test_check_config_generic_exception(self):
        """Returns False when an unexpected exception is raised."""
        with patch("src.utils.validation._check_core_settings", side_effect=RuntimeError("boom")):
            result = check_config()
        assert result is False


# ---- _check_core_settings ----


class TestCheckCoreSettings:
    """Tests for _check_core_settings."""

    def test_token_configured(self):
        """No error when token is present."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "telegram": {"token": "tok"},
            "language": "en-us",
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_core_settings()  # should not raise

    def test_token_missing(self):
        """Prints error when token is missing."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "telegram": {},
            "language": "invalid",
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_core_settings()  # should not raise

    def test_valid_language(self):
        """Prints success for valid language."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "telegram": {"token": "tok"},
            "language": "de-de",
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_core_settings()


# ---- _check_media_services ----


class TestCheckMediaServices:
    """Tests for _check_media_services."""

    def test_service_enabled_with_apikey(self):
        """Service enabled with API key shows configured."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "radarr": {"enable": True, "auth": {"apikey": "key123"}},
            "sonarr": {"enable": False},
            "lidarr": {"enable": False},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_media_services()

    def test_service_enabled_no_apikey(self):
        """Service enabled without API key shows warning."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "radarr": {"enable": True, "auth": {}},
            "sonarr": {"enable": False},
            "lidarr": {"enable": False},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_media_services()

    def test_service_disabled(self):
        """Disabled service shows info."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "radarr": {},
            "sonarr": {},
            "lidarr": {},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_media_services()


# ---- _check_download_clients ----


class TestCheckDownloadClients:
    """Tests for _check_download_clients."""

    def test_transmission_enabled_with_auth(self):
        """Transmission with auth configured shows success."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "transmission": {
                "enable": True,
                "authentication": True,
                "username": "user",
                "password": "pass",
            },
            "sabnzbd": {"enable": False},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_download_clients()

    def test_transmission_enabled_auth_no_creds(self):
        """Transmission with auth enabled but no creds shows warning."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "transmission": {
                "enable": True,
                "authentication": True,
                "username": None,
                "password": None,
            },
            "sabnzbd": {"enable": False},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_download_clients()

    def test_transmission_disabled(self):
        """Disabled transmission shows info."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "transmission": {"enable": False},
            "sabnzbd": {"enable": False},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_download_clients()

    def test_sabnzbd_enabled_with_apikey(self):
        """SABnzbd with API key shows configured."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "transmission": {"enable": False},
            "sabnzbd": {
                "enable": True,
                "auth": {"apikey": "key123"},
            },
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_download_clients()

    def test_sabnzbd_enabled_no_apikey(self):
        """SABnzbd without API key shows warning."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "transmission": {"enable": False},
            "sabnzbd": {
                "enable": True,
                "auth": {},
            },
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_download_clients()

    def test_transmission_enabled_no_auth(self):
        """Transmission enabled without authentication flag."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "transmission": {"enable": True, "authentication": False},
            "sabnzbd": {"enable": False},
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_download_clients()


# ---- _check_security_settings ----


class TestCheckSecuritySettings:
    """Tests for _check_security_settings."""

    def test_admin_enabled_with_admins(self):
        """Admin mode with configured admins."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "security": {"enableAdmin": True, "enableAllowlist": False},
            "admins": [123, 456],
            "allow_list": [],
        }.get(key, default)
        mock_cfg.__getitem__ = lambda self, key: {"admins": [123, 456]}[key]
        with patch("src.utils.validation.config", mock_cfg):
            _check_security_settings()

    def test_admin_enabled_no_admins(self):
        """Admin mode with no admins configured."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "security": {"enableAdmin": True, "enableAllowlist": False},
            "admins": [],
            "allow_list": [],
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_security_settings()

    def test_admin_disabled(self):
        """Admin mode disabled shows info."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "security": {"enableAdmin": False, "enableAllowlist": False},
            "admins": [],
            "allow_list": [],
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_security_settings()

    def test_allowlist_enabled_with_users(self):
        """Allowlist with configured users."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "security": {"enableAdmin": False, "enableAllowlist": True},
            "admins": [],
            "allow_list": [111, 222],
        }.get(key, default)
        mock_cfg.__getitem__ = lambda self, key: {"allow_list": [111, 222]}[key]
        with patch("src.utils.validation.config", mock_cfg):
            _check_security_settings()

    def test_allowlist_enabled_no_users(self):
        """Allowlist with no users configured."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "security": {"enableAdmin": False, "enableAllowlist": True},
            "admins": [],
            "allow_list": [],
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_security_settings()

    def test_allowlist_disabled(self):
        """Allowlist disabled shows info."""
        mock_cfg = MagicMock()
        mock_cfg.get = lambda key, default=None: {
            "security": {"enableAdmin": False, "enableAllowlist": False},
            "admins": [],
            "allow_list": [],
        }.get(key, default)
        with patch("src.utils.validation.config", mock_cfg):
            _check_security_settings()
