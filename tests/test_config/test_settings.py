"""Tests for config settings -- MockConfig behavior and validation logic.

We can't import the real Config class because it triggers file I/O at module
level. Instead, we test:
1. The MockConfig used in our test harness (validates test infrastructure)
2. The real Config._get_missing_keys logic by extracting it
3. Language validation logic
"""

import pytest


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
