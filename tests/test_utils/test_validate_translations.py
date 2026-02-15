"""Tests for src/utils/validate_translations.py -- pure functions."""

from src.utils.validate_translations import (
    load_yaml,
    get_all_keys,
    get_nested_value,
    get_format_placeholders,
    validate_translation,
    check_emoji_consistency,
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
