"""Tests for src/utils/validation.py"""

import pytest

from src.utils.error_handler import ValidationError
from src.utils.validation import (
    RequiredValidator,
    TypeValidator,
    RangeValidator,
    validate_data,
)


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
