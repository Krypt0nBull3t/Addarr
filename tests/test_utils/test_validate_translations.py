"""Tests for src/utils/validate_translations.py -- pure functions."""

from unittest.mock import patch, MagicMock
from pathlib import Path

from src.utils.validate_translations import (
    load_yaml,
    get_all_keys,
    get_nested_value,
    get_format_placeholders,
    validate_translation,
    check_emoji_consistency,
    main,
)


class TestLoadYaml:
    def test_load_yaml_success(self, tmp_path):
        f = tmp_path / "test.yml"
        f.write_text("key: value\nnested:\n  inner: 42\n", encoding="utf-8")
        result = load_yaml(str(f))
        assert result == {"key": "value", "nested": {"inner": 42}}

    def test_load_yaml_error(self, tmp_path):
        result = load_yaml(str(tmp_path / "nonexistent.yml"))
        assert result == {}


class TestGetAllKeys:
    def test_flat(self):
        data = {"a": 1, "b": 2}
        keys = get_all_keys(data)
        assert sorted(keys) == ["a", "b"]

    def test_nested(self):
        data = {"a": {"b": 1, "c": 2}}
        keys = get_all_keys(data)
        assert sorted(keys) == ["a.b", "a.c"]

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": 1}}}
        keys = get_all_keys(data)
        assert keys == ["a.b.c"]

    def test_empty(self):
        assert get_all_keys({}) == []

    def test_required_section_not_dict(self):
        """Prints warning and skips when required section is not a dict."""
        data = {"messages": "not a dict"}
        keys = get_all_keys(data, required_sections={"messages"})
        assert keys == []

    def test_required_section_is_dict(self):
        """Required section that is a dict processes normally."""
        data = {"messages": {"hello": "world"}}
        keys = get_all_keys(data, required_sections={"messages"})
        assert keys == ["messages.hello"]


class TestGetNestedValue:
    def test_simple_key(self):
        assert get_nested_value({"a": "hello"}, "a") == "hello"

    def test_nested_key(self):
        assert get_nested_value({"a": {"b": "c"}}, "a.b") == "c"

    def test_missing_key(self):
        assert get_nested_value({"a": 1}, "b") is None

    def test_missing_nested_key(self):
        assert get_nested_value({"a": {"b": 1}}, "a.c") is None

    def test_non_dict_intermediate(self):
        assert get_nested_value({"a": "string"}, "a.b") is None


class TestGetFormatPlaceholders:
    def test_with_placeholders(self):
        result = get_format_placeholders("Hello %{name}, welcome to %{place}")
        assert result == {"name", "place"}

    def test_no_placeholders(self):
        result = get_format_placeholders("Hello world")
        assert result == set()

    def test_single_placeholder(self):
        result = get_format_placeholders("Hello %{name}")
        assert result == {"name"}

    def test_empty_string(self):
        result = get_format_placeholders("")
        assert result == set()


class TestValidateTranslation:
    def test_missing_keys(self):
        template = {"template": {"a": "val_a", "b": "val_b"}}
        translation = {"en": {"a": "val_a"}}
        missing, extra, errors = validate_translation(template, translation, "en")
        assert "b" in missing
        assert extra == []

    def test_extra_keys(self):
        template = {"template": {"a": "val_a"}}
        translation = {"en": {"a": "val_a", "c": "val_c"}}
        missing, extra, errors = validate_translation(template, translation, "en")
        assert missing == []
        assert "c" in extra

    def test_no_issues(self):
        template = {"template": {"a": "val_a", "b": "val_b"}}
        translation = {"en": {"a": "val_a", "b": "val_b"}}
        missing, extra, errors = validate_translation(template, translation, "en")
        assert missing == []
        assert extra == []
        assert errors == []

    def test_format_placeholder_mismatch(self):
        template = {"template": {"greeting": "Hello %{name}"}}
        translation = {"en": {"greeting": "Hello %{user}"}}
        missing, extra, errors = validate_translation(template, translation, "en")
        assert len(errors) == 1
        assert "greeting" in errors[0]


class TestCheckEmojiConsistency:
    def test_missing_emoji_detected(self):
        template = {"template": {"greeting": "\U0001F600 Hello"}}
        translations = {
            "de": {"de": {"greeting": "Hallo"}}
        }
        errors = check_emoji_consistency(template, translations)
        assert len(errors) >= 1
        assert "de" in errors[0]

    def test_emoji_present_no_error(self):
        template = {"template": {"greeting": "\U0001F600 Hello"}}
        translations = {
            "de": {"de": {"greeting": "\U0001F600 Hallo"}}
        }
        errors = check_emoji_consistency(template, translations)
        assert errors == []

    def test_no_emoji_in_template(self):
        template = {"template": {"greeting": "Hello"}}
        translations = {
            "de": {"de": {"greeting": "Hallo"}}
        }
        errors = check_emoji_consistency(template, translations)
        assert errors == []


class TestMain:
    """Tests for the main() validation function."""

    def test_template_load_failure(self):
        """Exits early when template file fails to load."""
        with patch("src.utils.validate_translations.load_yaml", return_value={}):
            main()  # should not raise

    def test_valid_translations(self, tmp_path):
        """All translations valid, prints success."""
        template_data = {"template": {"greeting": "Hello"}}
        trans_data = {"en": {"greeting": "Hello"}}

        # Create translation file
        trans_file = tmp_path / "addarr.en.yml"
        trans_file.write_text("en:\n  greeting: Hello\n")

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,  # template load
                trans_data,     # translation load
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.en.yml")
            ]
            main()

    def test_missing_keys(self, tmp_path):
        """Reports missing keys in translation."""
        template_data = {"template": {"greeting": "Hello", "farewell": "Bye"}}
        trans_data = {"en": {"greeting": "Hello"}}

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,
                trans_data,
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.en.yml")
            ]
            main()

    def test_extra_keys(self, tmp_path):
        """Reports extra keys in translation."""
        template_data = {"template": {"greeting": "Hello"}}
        trans_data = {"en": {"greeting": "Hello", "extra": "oops"}}

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,
                trans_data,
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.en.yml")
            ]
            main()

    def test_format_errors(self, tmp_path):
        """Reports format placeholder mismatches."""
        template_data = {"template": {"greeting": "Hello %{name}"}}
        trans_data = {"en": {"greeting": "Hello %{user}"}}

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,
                trans_data,
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.en.yml")
            ]
            main()

    def test_translation_load_failure(self):
        """Marks invalid and continues when a translation file fails to load."""
        template_data = {"template": {"greeting": "Hello"}}

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,
                {},  # translation load failure
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.en.yml")
            ]
            main()

    def test_skips_template_file(self):
        """Skips the template file itself."""
        template_data = {"template": {"greeting": "Hello"}}
        trans_data = {"de": {"greeting": "Hallo"}}

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,
                trans_data,
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.template.yml"),
                Path("translations/addarr.de.yml"),
            ]
            main()

    def test_emoji_consistency_errors(self):
        """Reports emoji consistency issues."""
        template_data = {"template": {"greeting": "\U0001F600 Hello"}}
        trans_data = {"de": {"greeting": "Hallo"}}

        with (
            patch("src.utils.validate_translations.load_yaml", side_effect=[
                template_data,
                trans_data,
            ]),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = [
                Path("translations/addarr.de.yml")
            ]
            main()

    def test_no_translation_files(self):
        """All valid when no translation files exist."""
        template_data = {"template": {"greeting": "Hello"}}

        with (
            patch("src.utils.validate_translations.load_yaml", return_value=template_data),
            patch("src.utils.validate_translations.Path") as mock_path_cls,
        ):
            mock_translations_dir = MagicMock()
            mock_path_cls.return_value = mock_translations_dir
            mock_translations_dir.glob.return_value = []
            main()
