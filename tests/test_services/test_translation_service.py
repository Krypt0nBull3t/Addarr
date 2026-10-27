"""
Tests for src/services/translation.py -- TranslationService singleton.

Note: The autouse mock_translation fixture in root conftest patches
_load_translations, so we set _translations manually in tests.
"""

from pathlib import Path
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

    def test_get_text_curly_placeholders(self):
        """%{name} placeholders, as used in the translation files, are filled."""
        service = TranslationService()
        TranslationService._translations = {
            "en-us": {"saved": "Port set to %{port} on %{host}."}
        }
        TranslationService._current_language = "en-us"

        result = service.get_text("saved", port=8080, host="pi")
        assert result == "Port set to 8080 on pi."

    def test_get_text_literal_percent_sign(self):
        """A literal % in a string without %(name)s placeholders is kept."""
        service = TranslationService()
        TranslationService._translations = {
            "en-us": {"limit": "Limit set to 50%"}
        }
        TranslationService._current_language = "en-us"

        assert service.get_text("limit") == "Limit set to 50%"

    def test_get_text_dotted_key(self):
        """A dotted key walks into a nested section."""
        service = TranslationService()
        TranslationService._translations = {
            "en-us": {"Sabnzbd": {"Speed": "Which speed?"}}
        }
        TranslationService._current_language = "en-us"

        assert service.get_text("Sabnzbd.Speed") == "Which speed?"

    def test_get_text_dotted_key_fallback_language(self):
        """A dotted key missing in the current language uses the fallback."""
        service = TranslationService()
        TranslationService._current_language = "de-de"
        TranslationService._fallback_language = "en-us"
        TranslationService._translations = {
            "de-de": {"Sabnzbd": {}},
            "en-us": {"Sabnzbd": {"Speed": "Which speed?"}},
        }

        assert service.get_text("Sabnzbd.Speed") == "Which speed?"

    def test_get_text_section_returns_key(self):
        """A key that names a whole section is not a string: return the key."""
        service = TranslationService()
        TranslationService._translations = {
            "en-us": {"Sabnzbd": {"Speed": "Which speed?"}}
        }
        TranslationService._current_language = "en-us"

        assert service.get_text("Sabnzbd") == "Sabnzbd"

    def test_get_text_default_when_missing(self):
        """default= is returned when the key is missing."""
        service = TranslationService()
        TranslationService._translations = {"en-us": {"hello": "Hello"}}
        TranslationService._current_language = "en-us"

        assert service.get_text("missing", default="Fallback") == "Fallback"
        assert service.get_text("hello", default="Fallback") == "Hello"

    def test_shipped_files_resolve_keys(self, monkeypatch):
        """Keys used by the handlers resolve and format in every shipped locale."""
        monkeypatch.chdir(Path(__file__).resolve().parents[2])
        TranslationService._translations = {}
        _real_load_translations(TranslationService)
        service = TranslationService()

        assert len(TranslationService._translations) == 10  # 9 locales + template
        for lang in TranslationService._translations:
            TranslationService._current_language = lang
            for key in ("Sabnzbd.Speed", "Sabnzbd.ChangedTo50",
                        "Settings.AdminOnly", "messages.NoExist"):
                assert service.get_text(key) != key, (lang, key)
            saved = service.get_text("WebhookPortSaved", port=8080)
            assert "8080" in saved and "%{" not in saved, lang
            for subject in ("movie", "series", "music"):
                message = service.get_message("NoExist", subject=subject)
                assert "WithArticle" not in message, (lang, subject)
                assert "%{" not in message, (lang, subject)


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
                "Movie": "Movie",
                "MovieWithArticle": "The movie",
                "messages": {
                    "searchFor": "%{subjectWithArticle} (%{subject}): %{title}",
                },
            }
        }

        result = service.get_message(
            "searchFor", subject="movie", title="Fight Club"
        )

        # Handlers pass "movie"; the subject keys are capitalized in the files
        assert result == "The movie (Movie): Fight Club"

    def test_get_message_without_subject(self):
        service = TranslationService()
        TranslationService._current_language = "en-us"
        TranslationService._translations = {
            "en-us": {
                "messages": {"generic": "A generic message"},
            }
        }

        result = service.get_message("generic")
        assert result == "A generic message"

    def test_get_message_with_title_only(self):
        service = TranslationService()
        TranslationService._current_language = "en-us"
        TranslationService._translations = {
            "en-us": {
                "messages": {"found": "Found: %{title}"},
            }
        }

        result = service.get_message("found", title="Fight Club")
        assert result == "Found: Fight Club"
