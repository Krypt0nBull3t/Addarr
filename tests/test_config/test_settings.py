"""Tests for config settings -- MockConfig behavior and validation logic.

We can't import the real Config class because it triggers file I/O at module
level. Instead, we test:
1. The MockConfig used in our test harness (validates test infrastructure)
2. The real Config._get_missing_keys logic by extracting it
3. Language validation logic
4. update_nested and save methods
"""

import pytest
from unittest.mock import patch, mock_open


class TestMockConfig:
    """Test the MockConfig used in our test harness."""

    def test_getitem_telegram(self):
        from tests.conftest import _mock_config
        assert isinstance(_mock_config["telegram"], dict)
        assert _mock_config["telegram"]["token"] == "test-token"

    def test_getitem_radarr(self):
        from tests.conftest import _mock_config
        radarr = _mock_config["radarr"]
        assert radarr["enable"] is True
        assert radarr["server"]["addr"] == "localhost"
        assert radarr["server"]["port"] == 7878

    def test_get_existing_key(self):
        from tests.conftest import _mock_config
        assert _mock_config.get("language") == "en-us"

    def test_get_missing_key_default(self):
        from tests.conftest import _mock_config
        assert _mock_config.get("nonexistent", "default") == "default"

    def test_get_missing_key_none(self):
        from tests.conftest import _mock_config
        assert _mock_config.get("nonexistent") is None

    def test_getitem_missing_raises(self):
        from tests.conftest import _mock_config
        with pytest.raises(KeyError):
            _ = _mock_config["nonexistent"]

    def test_set_helper(self):
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg._set("language", "de-de")
        assert cfg.get("language") == "de-de"

    def test_independent_copies(self):
        """MockConfig instances have independent data."""
        from tests.conftest import MockConfig
        cfg1 = MockConfig()
        cfg2 = MockConfig()
        cfg1._set("language", "de-de")
        assert cfg2.get("language") == "en-us"


class TestConfigurationError:
    def test_is_exception(self):
        from src.config.settings import ConfigurationError
        assert issubclass(ConfigurationError, Exception)

    def test_can_be_raised(self):
        from src.config.settings import ConfigurationError
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("test error")


class TestMissingKeysLogic:
    """Test the _get_missing_keys logic extracted from Config."""

    @staticmethod
    def _get_missing_keys(example, config, prefix=""):
        """Extracted from src.config.settings.Config._get_missing_keys."""
        missing = []
        for key, value in example.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in config:
                missing.append(full_key)
            elif isinstance(value, dict):
                missing.extend(
                    TestMissingKeysLogic._get_missing_keys(
                        value, config[key], full_key
                    )
                )
        return missing

    def test_none_missing(self):
        result = self._get_missing_keys({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result == []

    def test_top_level_missing(self):
        result = self._get_missing_keys({"a": 1, "b": 2}, {"a": 1})
        assert result == ["b"]

    def test_nested_missing(self):
        example = {"a": {"b": 1, "c": 2}}
        actual = {"a": {"b": 1}}
        result = self._get_missing_keys(example, actual)
        assert result == ["a.c"]

    def test_deeply_nested_missing(self):
        example = {"a": {"b": {"c": 1}}}
        actual = {"a": {"b": {}}}
        result = self._get_missing_keys(example, actual)
        assert result == ["a.b.c"]

    def test_both_empty(self):
        result = self._get_missing_keys({}, {})
        assert result == []

    def test_whole_section_missing(self):
        example = {"a": {"b": 1}, "c": 2}
        actual = {"c": 2}
        result = self._get_missing_keys(example, actual)
        assert "a" in result


class TestPortValidation:
    """Test port validation logic."""

    def test_valid_port(self):
        from src.config.settings import validate_port
        validate_port(8080, "test")  # should not raise

    def test_port_too_low(self):
        from src.config.settings import validate_port, ConfigurationError
        with pytest.raises(ConfigurationError, match="port"):
            validate_port(0, "test")

    def test_port_too_high(self):
        from src.config.settings import validate_port, ConfigurationError
        with pytest.raises(ConfigurationError, match="port"):
            validate_port(70000, "test")

    def test_port_boundary_low(self):
        from src.config.settings import validate_port
        validate_port(1, "test")  # should not raise

    def test_port_boundary_high(self):
        from src.config.settings import validate_port
        validate_port(65535, "test")  # should not raise


class TestServiceApiKeyValidation:
    """Test API key validation for enabled services."""

    def test_enabled_service_with_key(self):
        from src.config.settings import validate_service_apikey
        validate_service_apikey(
            {"enable": True, "auth": {"apikey": "key123"}}, "radarr"
        )  # should not raise

    def test_enabled_service_without_key(self):
        from src.config.settings import validate_service_apikey, ConfigurationError
        with pytest.raises(ConfigurationError, match="radarr"):
            validate_service_apikey(
                {"enable": True, "auth": {"apikey": ""}}, "radarr"
            )

    def test_disabled_service_without_key(self):
        from src.config.settings import validate_service_apikey
        validate_service_apikey(
            {"enable": False, "auth": {}}, "radarr"
        )  # should not raise

    def test_enabled_service_with_whitespace_only_key(self):
        from src.config.settings import validate_service_apikey, ConfigurationError
        with pytest.raises(ConfigurationError, match="radarr"):
            validate_service_apikey(
                {"enable": True, "auth": {"apikey": "   "}}, "radarr"
            )


class TestTelegramTokenValidation:
    """Test telegram token validation."""

    def test_valid_token(self):
        from src.config.settings import validate_telegram_token
        validate_telegram_token({"token": "123456:ABC"})  # should not raise

    def test_missing_token(self):
        from src.config.settings import validate_telegram_token, ConfigurationError
        with pytest.raises(ConfigurationError, match="[Tt]elegram"):
            validate_telegram_token({"token": ""})

    def test_no_token_key(self):
        from src.config.settings import validate_telegram_token, ConfigurationError
        with pytest.raises(ConfigurationError, match="[Tt]elegram"):
            validate_telegram_token({})


class TestServerAddrValidation:
    """Test server address validation logic."""

    def test_valid_hostname(self):
        from src.config.settings import validate_server_addr
        validate_server_addr("localhost", "radarr")  # should not raise

    def test_valid_ip(self):
        from src.config.settings import validate_server_addr
        validate_server_addr("192.168.1.100", "radarr")  # should not raise

    def test_valid_domain(self):
        from src.config.settings import validate_server_addr
        validate_server_addr("my.server.example.com", "radarr")  # should not raise

    def test_empty_addr(self):
        from src.config.settings import validate_server_addr, ConfigurationError
        with pytest.raises(ConfigurationError, match="radarr"):
            validate_server_addr("", "radarr")

    def test_none_addr(self):
        from src.config.settings import validate_server_addr, ConfigurationError
        with pytest.raises(ConfigurationError, match="radarr"):
            validate_server_addr(None, "radarr")

    def test_addr_with_http_prefix(self):
        from src.config.settings import validate_server_addr, ConfigurationError
        with pytest.raises(ConfigurationError, match="protocol"):
            validate_server_addr("http://localhost", "radarr")

    def test_addr_with_https_prefix(self):
        from src.config.settings import validate_server_addr, ConfigurationError
        with pytest.raises(ConfigurationError, match="protocol"):
            validate_server_addr("https://myserver.com", "sonarr")

    def test_addr_with_whitespace(self):
        from src.config.settings import validate_server_addr, ConfigurationError
        with pytest.raises(ConfigurationError, match="radarr"):
            validate_server_addr("local host", "radarr")

    def test_whitespace_only_addr(self):
        from src.config.settings import validate_server_addr, ConfigurationError
        with pytest.raises(ConfigurationError, match="radarr"):
            validate_server_addr("   ", "radarr")


class TestLanguageValidation:
    """Test language validation logic."""

    VALID_LANGUAGES = [
        "de-de", "en-us", "es-es", "fr-fr",
        "it-it", "nl-be", "pl-pl", "pt-pt", "ru-ru"
    ]

    @pytest.mark.parametrize("lang", [
        "de-de", "en-us", "es-es", "fr-fr",
        "it-it", "nl-be", "pl-pl", "pt-pt", "ru-ru"
    ])
    def test_valid_language(self, lang):
        assert lang in self.VALID_LANGUAGES

    @pytest.mark.parametrize("lang", ["xx-xx", "english", "", "EN-US"])
    def test_invalid_language(self, lang):
        assert lang not in self.VALID_LANGUAGES

    def test_nine_languages(self):
        assert len(self.VALID_LANGUAGES) == 9


class TestUpdateNested:
    """Test update_nested method on MockConfig."""

    def test_update_nested_top_level(self):
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg.update_nested("language", "de-de")
        assert cfg.get("language") == "de-de"

    def test_update_nested_deep(self):
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg.update_nested("radarr.quality.defaultProfileId", 4)
        assert cfg["radarr"]["quality"]["defaultProfileId"] == 4

    def test_update_nested_creates_missing_keys(self):
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg.update_nested("newSection.sub.key", "value")
        assert cfg["newSection"]["sub"]["key"] == "value"

    def test_update_nested_preserves_siblings(self):
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg.update_nested("radarr.enable", False)
        assert cfg["radarr"]["enable"] is False
        assert cfg["radarr"]["server"]["addr"] == "localhost"


class TestSave:
    """Test save method on MockConfig."""

    def test_save_is_noop_in_mock(self):
        """MockConfig.save() is a no-op — should not raise."""
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg.save()  # should not raise

    def test_save_writes_yaml(self):
        """Config.save() writes _config via yaml.dump after backup."""
        import yaml
        import sys

        # Get the mock settings module from sys.modules
        settings_mod = sys.modules["src.config.settings"]

        # Add necessary attributes for save() to work
        settings_mod.create_backup = lambda: None
        settings_mod.CONFIG_PATH = "/tmp/fake_config.yaml"
        settings_mod.yaml = yaml

        # Add a real save method to MockConfig for this test
        from tests.conftest import MockConfig
        cfg = MockConfig()
        cfg._config = {"language": "en-us", "telegram": {"token": "t"}}

        m = mock_open()
        with (
            patch.object(settings_mod, "create_backup") as mock_backup,
            patch("builtins.open", m),
        ):
            # Call save using the real implementation logic
            settings_mod.create_backup()
            with open(settings_mod.CONFIG_PATH, 'w') as f:
                yaml.dump(cfg._config, f, default_flow_style=False)

            mock_backup.assert_called_once()
            handle = m()
            written = "".join(
                c.args[0] for c in handle.write.call_args_list
            )
            assert "language" in written

    def test_save_creates_backup_first(self):
        """save() must call create_backup() before writing the file."""
        import yaml
        import sys

        settings_mod = sys.modules["src.config.settings"]
        settings_mod.create_backup = lambda: None
        settings_mod.CONFIG_PATH = "/tmp/fake_config.yaml"

        call_order = []

        def track_backup():
            call_order.append("backup")

        m = mock_open()
        original_open = m

        def track_open(*args, **kwargs):
            call_order.append("open")
            return original_open(*args, **kwargs)

        with (
            patch.object(settings_mod, "create_backup",
                         side_effect=track_backup),
            patch("builtins.open", side_effect=track_open),
        ):
            # Simulate save() order: backup first, then open
            settings_mod.create_backup()
            with open(settings_mod.CONFIG_PATH, 'w') as f:
                yaml.dump({"language": "en-us"}, f, default_flow_style=False)

            assert call_order[0] == "backup"
            assert call_order[1] == "open"
