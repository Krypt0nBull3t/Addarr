"""
Tests for src/services/translation.py -- TranslationService singleton.

Note: The autouse mock_translation fixture in root conftest patches
_load_translations, so we set _translations manually in tests.
"""

from unittest.mock import patch, MagicMock

from src.services.translation import TranslationService


# Keep a reference to the REAL _load_translations before the autouse fixture
# patches it. We need this so we can call it from tests that verify loading.
_real_load_translations = TranslationService._load_translations.__func__


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestTranslationServiceSingleton:
    def test_singleton(self):
        a = TranslationService()
        b = TranslationService()
        assert a is b


# ---------------------------------------------------------------------------
# _load_translations
# ---------------------------------------------------------------------------


class TestLoadTranslations:
    """Tests for _load_translations.

    The autouse mock_translation fixture patches _load_translations to a noop.
    These tests call the REAL implementation via the saved reference.
    """

    def test_load_translations_dir_not_found(self):
        """When translations dir doesn't exist, logs error and returns."""
        TranslationService._translations = {}

        with patch("src.services.translation.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            _real_load_translations(TranslationService)

        assert TranslationService._translations == {}

    def test_load_translations_success(self, tmp_path):
        """Successfully loads translation YAML files."""
        TranslationService._translations = {}

        trans_dir = tmp_path / "translations"
        trans_dir.mkdir()
        trans_file = trans_dir / "addarr.en-us.yml"
        trans_file.write_text("en-us:\n  hello: Hello World\n")

        with patch("src.services.translation.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [trans_file]
            mock_path.return_value = mock_dir

            _real_load_translations(TranslationService)

        assert "en-us" in TranslationService._translations
        assert TranslationService._translations["en-us"]["hello"] == "Hello World"

    def test_load_translations_invalid_format(self, tmp_path):
        """When YAML is valid but doesn't contain lang key, logs warning."""
        TranslationService._translations = {}

        trans_dir = tmp_path / "translations"
        trans_dir.mkdir()
        trans_file = trans_dir / "addarr.de-de.yml"
        trans_file.write_text("other_key:\n  hello: Hallo\n")

        with patch("src.services.translation.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [trans_file]
            mock_path.return_value = mock_dir

            _real_load_translations(TranslationService)

        assert "de-de" not in TranslationService._translations

    def test_load_translations_yaml_error(self, tmp_path):
        """When file causes an exception during open, logs error."""
        TranslationService._translations = {}

        mock_file = MagicMock()
        mock_file.stem = "addarr.bad"

        with patch("src.services.translation.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [mock_file]
            mock_path.return_value = mock_dir

            with patch("builtins.open", side_effect=Exception("File read error")):
                _real_load_translations(TranslationService)

        assert "bad" not in TranslationService._translations

    def test_load_translations_empty_data(self, tmp_path):
        """When YAML file parses to None, skips it."""
        TranslationService._translations = {}

        trans_dir = tmp_path / "translations"
        trans_dir.mkdir()
        trans_file = trans_dir / "addarr.empty.yml"
        trans_file.write_text("")

        with patch("src.services.translation.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [trans_file]
            mock_path.return_value = mock_dir

            _real_load_translations(TranslationService)

        assert "empty" not in TranslationService._translations


# ---------------------------------------------------------------------------
# get_text
# ---------------------------------------------------------------------------


class TestGetText:
    def test_get_text_found(self):
        service = TranslationService()
        TranslationService._translations = {"en-us": {"hello": "Hello World"}}
        TranslationService._current_language = "en-us"

        result = service.get_text("hello")
        assert result == "Hello World"

    def test_get_text_fallback_language(self):
        service = TranslationService()
        TranslationService._current_language = "de-de"
        TranslationService._fallback_language = "en-us"
        TranslationService._translations = {
            "de-de": {},
            "en-us": {"greeting": "Hello from fallback"},
        }

        result = service.get_text("greeting")
        assert result == "Hello from fallback"

    def test_get_text_not_found(self):
        service = TranslationService()
        TranslationService._translations = {"en-us": {}}
        TranslationService._current_language = "en-us"

        result = service.get_text("nonexistent.key")
        assert result == "nonexistent.key"

    def test_get_text_with_format_params(self):
        service = TranslationService()
        TranslationService._translations = {
            "en-us": {"welcome": "Hello %(name)s"}
        }
        TranslationService._current_language = "en-us"

        result = service.get_text("welcome", name="World")
        assert result == "Hello World"

    def test_get_text_format_exception(self):
        """When format params cause an error, return the key."""
        service = TranslationService()
        TranslationService._translations = {
            "en-us": {"broken": "Hello %(name)s %(missing)s"}
        }
        TranslationService._current_language = "en-us"

        result = service.get_text("broken", name="World")
        # Should return the key because %(missing)s causes KeyError
        assert result == "broken"


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_current_language_property(self):
        service = TranslationService()
        TranslationService._current_language = "fr-fr"

        assert service.current_language == "fr-fr"

    def test_fallback_language_property(self):
        service = TranslationService()
        TranslationService._fallback_language = "en-us"

        assert service.fallback_language == "en-us"


# ---------------------------------------------------------------------------
# get_message
# ---------------------------------------------------------------------------


class TestGetMessage:
    def test_get_message_with_subject(self):
        service = TranslationService()
        TranslationService._current_language = "en-us"
        TranslationService._translations = {
            "en-us": {
                "movie": "movie",
                "movieWithArticle": "a movie",
                "messages.searchFor": (
                    "Searching for %(subject)s: %(title)s"
                ),
            }
        }

        result = service.get_message(
            "searchFor", subject="movie", title="Fight Club"
        )

        assert "movie" in result
        assert "Fight Club" in result

    def test_get_message_without_subject(self):
        service = TranslationService()
        TranslationService._current_language = "en-us"
        TranslationService._translations = {
            "en-us": {
                "messages.generic": "A generic message",
            }
        }

        result = service.get_message("generic")
        assert result == "A generic message"

    def test_get_message_with_title_only(self):
        service = TranslationService()
        TranslationService._current_language = "en-us"
        TranslationService._translations = {
            "en-us": {
                "messages.found": "Found: %(title)s",
            }
        }

        result = service.get_message("found", title="Fight Club")
        assert result == "Found: Fight Club"
