"""
Tests for src/services/translation.py -- TranslationService singleton.

Note: The autouse mock_translation fixture in root conftest patches
_load_translations, so we set _translations manually in tests.
"""

import pytest

from src.services.translation import TranslationService


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestTranslationServiceSingleton:
    def test_singleton(self):
        a = TranslationService()
        b = TranslationService()
        assert a is b


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


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_current_language_property(self):
        service = TranslationService()
        TranslationService._current_language = "fr-fr"

        assert service.current_language == "fr-fr"


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
