"""Tests for src/utils/validation.py"""

import pytest
from unittest.mock import patch, MagicMock

from src.utils.error_handler import ValidationError
from src.utils.validation import (
    Validator,
    RequiredValidator,
    TypeValidator,
    RangeValidator,
    validate_data,
    check_dependencies,
    check_config,
    _check_core_settings,
    _check_media_services,
    _check_download_clients,
    _check_security_settings,
    parse_requirements,
    get_installed_packages,
)


# ---- Validator base class ----


class TestValidator:
    """Tests for the abstract Validator base class."""

    def test_validate_raises_not_implemented(self):
        """Base Validator.validate raises NotImplementedError."""
        v = Validator("field")
        with pytest.raises(NotImplementedError):
            v.validate("anything")


# ---- RequiredValidator ----


class TestRequiredValidator:
    """Tests for RequiredValidator."""

    def test_required_validator_passes(self):
        """Non-None, non-empty value passes without raising."""
        v = RequiredValidator("name")
        v.validate("hello")  # should not raise

    def test_required_validator_fails_none(self):
        """None raises ValidationError."""
        v = RequiredValidator("name")
        with pytest.raises(ValidationError):
            v.validate(None)

    def test_required_validator_fails_empty_string(self):
        """Empty string raises ValidationError."""
        v = RequiredValidator("name")
        with pytest.raises(ValidationError):
            v.validate("")


# ---- TypeValidator ----


class TestTypeValidator:
    """Tests for TypeValidator."""

    def test_type_validator_passes(self):
        """Correct type passes without raising."""
        v = TypeValidator("port", int)
        v.validate(8080)  # should not raise

    def test_type_validator_fails(self):
        """Wrong type raises ValidationError."""
        v = TypeValidator("port", int)
        with pytest.raises(ValidationError):
            v.validate("not-an-int")


# ---- RangeValidator ----


class TestRangeValidator:
    """Tests for RangeValidator."""

    def test_range_validator_passes(self):
        """Value within range passes without raising."""
        v = RangeValidator("port", min_value=1, max_value=65535)
        v.validate(8080)  # should not raise

    def test_range_validator_too_low(self):
        """Value below min_value raises ValidationError."""
        v = RangeValidator("port", min_value=1, max_value=65535)
        with pytest.raises(ValidationError):
            v.validate(0)

    def test_range_validator_too_high(self):
        """Value above max_value raises ValidationError."""
        v = RangeValidator("port", min_value=1, max_value=65535)
        with pytest.raises(ValidationError):
            v.validate(70000)

    def test_range_validator_non_numeric(self):
        """Non-numeric value raises ValidationError."""
        v = RangeValidator("port", min_value=1, max_value=65535)
        with pytest.raises(ValidationError):
            v.validate("not-a-number")


# ---- validate_data ----


class TestValidateData:
    """Tests for validate_data helper."""

    def test_validate_data_all_pass(self):
        """Valid data passes all validators without raising."""
        data = {"name": "Addarr", "port": 8080}
        validators = {
            "name": [RequiredValidator("name"), TypeValidator("name", str)],
            "port": [
                RequiredValidator("port"),
                TypeValidator("port", int),
                RangeValidator("port", min_value=1, max_value=65535),
            ],
        }
        validate_data(data, validators)  # should not raise

    def test_validate_data_fails(self):
        """Invalid data raises ValidationError."""
        data = {"name": "", "port": 8080}
        validators = {
            "name": [RequiredValidator("name")],
        }
        with pytest.raises(ValidationError):
            validate_data(data, validators)


# ---- parse_requirements / get_installed_packages ----


class TestParseRequirements:
    """Tests for parse_requirements."""

    def test_parse_requirements_returns_list(self, tmp_path, monkeypatch):
        """parse_requirements returns list of package names."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.28\npyyaml==6.0\ncolorama\n")
        monkeypatch.chdir(tmp_path)

        result = parse_requirements()
        assert isinstance(result, list)
        assert "requests" in result
        assert "pyyaml" in result
        assert "colorama" in result

    def test_parse_requirements_skips_comments_and_blanks(self, tmp_path, monkeypatch):
        """parse_requirements skips comment lines and blank lines."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# This is a comment\nrequests\n\n# Another comment\npyyaml\n")
        monkeypatch.chdir(tmp_path)

        result = parse_requirements()
        assert len(result) == 2
        assert "requests" in result
        assert "pyyaml" in result

    def test_parse_requirements_custom_filename(self, tmp_path, monkeypatch):
        """parse_requirements accepts a custom filename."""
        req_file = tmp_path / "custom.txt"
        req_file.write_text("flask\n")
        monkeypatch.chdir(tmp_path)

        result = parse_requirements("custom.txt")
        assert result == ["flask"]

    def test_parse_requirements_missing_file(self, tmp_path, monkeypatch):
        """parse_requirements returns empty list when file is missing."""
        monkeypatch.chdir(tmp_path)

        result = parse_requirements()
        assert result == []


class TestGetInstalledPackages:
    """Tests for get_installed_packages."""

    def test_get_installed_packages_returns_set(self):
        """get_installed_packages returns a set of lowercase package names."""
        result = get_installed_packages()
        assert isinstance(result, set)
        # pytest itself should be installed
        assert "pytest" in result

    def test_get_installed_packages_returns_empty_on_error(self):
        """get_installed_packages returns empty set when subprocess fails."""
        with patch("subprocess.run", side_effect=OSError("pip not found")):
            result = get_installed_packages()
        assert result == set()


# ---- check_dependencies ----


class TestCheckDependencies:
    """Tests for check_dependencies."""

    def test_no_requirements(self):
        """Returns False when parse_requirements returns empty."""
        with patch("src.utils.validation.parse_requirements", return_value=[]):
            result = check_dependencies()
        assert result is False

    def test_no_requirements_none(self):
        """Returns False when parse_requirements returns None."""
        with patch("src.utils.validation.parse_requirements", return_value=None):
            result = check_dependencies()
        assert result is False

    def test_all_installed(self):
        """Returns True when all packages are installed."""
        with (
            patch("src.utils.validation.parse_requirements", return_value=["requests", "pyyaml"]),
            patch("src.utils.validation.get_installed_packages", return_value={"requests", "pyyaml"}),
        ):
            result = check_dependencies()
        assert result is True

    def test_missing_install_yes(self):
        """Returns True when user chooses to install missing deps."""
        with (
            patch("src.utils.validation.parse_requirements", return_value=["missing-pkg"]),
            patch("src.utils.validation.get_installed_packages", return_value=set()),
            patch("builtins.input", return_value="y"),
            patch("subprocess.check_call") as mock_install,
        ):
            result = check_dependencies()
        assert result is True
        mock_install.assert_called_once()

    def test_missing_install_fail(self):
        """Returns False when pip install fails."""
        import subprocess
        with (
            patch("src.utils.validation.parse_requirements", return_value=["missing-pkg"]),
            patch("src.utils.validation.get_installed_packages", return_value=set()),
            patch("builtins.input", return_value="y"),
            patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "pip")),
        ):
            result = check_dependencies()
        assert result is False

    def test_missing_decline(self):
        """Returns False when user declines to install."""
        with (
            patch("src.utils.validation.parse_requirements", return_value=["missing-pkg"]),
            patch("src.utils.validation.get_installed_packages", return_value=set()),
            patch("builtins.input", return_value="n"),
        ):
            result = check_dependencies()
        assert result is False

    def test_missing_invalid_then_no(self):
        """Prompts again after invalid input, then declines."""
        with (
            patch("src.utils.validation.parse_requirements", return_value=["missing-pkg"]),
            patch("src.utils.validation.get_installed_packages", return_value=set()),
            patch("builtins.input", side_effect=["maybe", "no"]),
        ):
            result = check_dependencies()
        assert result is False

    def test_underscore_hyphen_normalization(self):
        """Packages with hyphens/underscores are found via normalization."""
        with (
            patch("src.utils.validation.parse_requirements", return_value=["my-package"]),
            patch("src.utils.validation.get_installed_packages", return_value={"my_package"}),
        ):
            result = check_dependencies()
        assert result is True


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

    def test_check_config_validation_error(self):
        """Returns False when a ValidationError is raised."""
        err = ValidationError("bad")
        err.message = "bad"
        with patch("src.utils.validation._check_core_settings", side_effect=err):
            result = check_config()
        assert result is False

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
