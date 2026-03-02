"""
Tests for PreferencesService.

Tests cover:
- get_preference / set_preference (generic key-value)
- get_view_mode returns "card" by default
- toggle_view_mode switches between "card" and "list"
- Missing file auto-creates empty prefs
- Corrupt JSON file resets gracefully
- Multi-user isolation
"""

import json
import os

import pytest


class TestPreferencesService:
    """Tests for the PreferencesService singleton."""

    @pytest.fixture(autouse=True)
    def setup_prefs_file(self, tmp_path):
        """Use a temp file for preferences, patch PREFERENCES_PATH."""
        self.prefs_path = str(tmp_path / "user_preferences.json")

        from unittest.mock import patch
        with patch("src.services.preferences.PREFERENCES_PATH", self.prefs_path):
            yield

    def _make_service(self):
        """Create a fresh PreferencesService (singleton reset happens via conftest)."""
        from src.services.preferences import PreferencesService
        return PreferencesService()

    # -- get_preference / set_preference --

    def test_get_preference_returns_default_when_not_set(self):
        svc = self._make_service()
        result = svc.get_preference("99999", "theme")
        assert result is None

    def test_get_preference_returns_custom_default(self):
        svc = self._make_service()
        result = svc.get_preference("99999", "theme", default="dark")
        assert result == "dark"

    def test_set_and_get_preference(self):
        svc = self._make_service()
        svc.set_preference("12345", "theme", "dark")
        assert svc.get_preference("12345", "theme") == "dark"

    def test_set_preference_persists_to_disk(self):
        svc = self._make_service()
        svc.set_preference("12345", "theme", "dark")

        # Read raw JSON to verify persistence
        with open(self.prefs_path, "r") as f:
            data = json.load(f)
        assert data["12345"]["theme"] == "dark"

    def test_set_preference_overwrites_existing(self):
        svc = self._make_service()
        svc.set_preference("12345", "theme", "dark")
        svc.set_preference("12345", "theme", "light")
        assert svc.get_preference("12345", "theme") == "light"

    # -- get_view_mode --

    def test_get_view_mode_returns_card_by_default(self):
        svc = self._make_service()
        assert svc.get_view_mode("12345") == "card"

    def test_get_view_mode_returns_stored_value(self):
        svc = self._make_service()
        svc.set_preference("12345", "view_mode", "list")
        assert svc.get_view_mode("12345") == "list"

    # -- toggle_view_mode --

    def test_toggle_view_mode_from_default_to_list(self):
        svc = self._make_service()
        result = svc.toggle_view_mode("12345")
        assert result == "list"
        assert svc.get_view_mode("12345") == "list"

    def test_toggle_view_mode_from_list_to_card(self):
        svc = self._make_service()
        svc.set_preference("12345", "view_mode", "list")
        result = svc.toggle_view_mode("12345")
        assert result == "card"
        assert svc.get_view_mode("12345") == "card"

    def test_toggle_view_mode_round_trip(self):
        svc = self._make_service()
        svc.toggle_view_mode("12345")  # card -> list
        svc.toggle_view_mode("12345")  # list -> card
        assert svc.get_view_mode("12345") == "card"

    # -- Missing file auto-creates --

    def test_missing_file_auto_creates_empty_prefs(self):
        assert not os.path.exists(self.prefs_path)
        svc = self._make_service()
        # Service should work without errors
        assert svc.get_view_mode("12345") == "card"

    def test_missing_file_created_on_first_write(self):
        assert not os.path.exists(self.prefs_path)
        svc = self._make_service()
        svc.set_preference("12345", "theme", "dark")
        assert os.path.exists(self.prefs_path)

    # -- Corrupt JSON resets gracefully --

    def test_corrupt_json_resets_to_empty(self):
        # Write corrupt data
        with open(self.prefs_path, "w") as f:
            f.write("{invalid json content!!!")

        svc = self._make_service()
        # Should not raise, should reset to empty
        assert svc.get_view_mode("12345") == "card"

    def test_corrupt_json_allows_new_writes(self):
        with open(self.prefs_path, "w") as f:
            f.write("not json")

        svc = self._make_service()
        svc.set_preference("12345", "theme", "dark")
        assert svc.get_preference("12345", "theme") == "dark"

    # -- Multi-user isolation --

    def test_multi_user_isolation(self):
        svc = self._make_service()
        svc.set_preference("111", "view_mode", "list")
        svc.set_preference("222", "view_mode", "card")

        assert svc.get_view_mode("111") == "list"
        assert svc.get_view_mode("222") == "card"

    def test_user_a_prefs_dont_affect_user_b(self):
        svc = self._make_service()
        svc.set_preference("111", "theme", "dark")

        # User 222 should have no theme set
        assert svc.get_preference("222", "theme") is None

    def test_toggle_one_user_doesnt_affect_another(self):
        svc = self._make_service()
        svc.toggle_view_mode("111")  # card -> list

        # User 222 should still be default
        assert svc.get_view_mode("222") == "card"
