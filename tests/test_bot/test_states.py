"""Tests for src/bot/states.py"""

from src.bot.states import States


class TestRemovedStates:
    """Tests that dead states have been removed"""

    def test_awaiting_setting_action_removed(self):
        """Dead state AWAITING_SETTING_ACTION no longer exists"""
        assert not hasattr(States, "AWAITING_SETTING_ACTION")

    def test_awaiting_delete_confirmation_removed(self):
        """Dead state AWAITING_DELETE_CONFIRMATION no longer exists"""
        assert not hasattr(States, "AWAITING_DELETE_CONFIRMATION")

    def test_awaiting_status_action_removed(self):
        """Dead state AWAITING_STATUS_ACTION no longer exists"""
        assert not hasattr(States, "AWAITING_STATUS_ACTION")

    def test_awaiting_speed_input_removed(self):
        """Dead state AWAITING_SPEED_INPUT no longer exists"""
        assert not hasattr(States, "AWAITING_SPEED_INPUT")


class TestSettingsStates:
    """Tests for settings sub-states"""

    def test_settings_states_exist(self):
        """SETTINGS_MENU, SETTINGS_LANGUAGE, SETTINGS_SERVICE,
        SETTINGS_QUALITY are defined"""
        assert hasattr(States, "SETTINGS_MENU")
        assert hasattr(States, "SETTINGS_LANGUAGE")
        assert hasattr(States, "SETTINGS_SERVICE")
        assert hasattr(States, "SETTINGS_QUALITY")

    def test_settings_states_are_strings(self):
        assert isinstance(States.SETTINGS_MENU, str)
        assert isinstance(States.SETTINGS_LANGUAGE, str)
        assert isinstance(States.SETTINGS_SERVICE, str)
        assert isinstance(States.SETTINGS_QUALITY, str)

    def test_settings_states_unique(self):
        settings_states = [
            States.SETTINGS_MENU,
            States.SETTINGS_LANGUAGE,
            States.SETTINGS_SERVICE,
            States.SETTINGS_QUALITY,
            States.SETTINGS_DOWNLOADS,
            States.SETTINGS_USERS,
        ]
        assert len(settings_states) == len(set(settings_states))


class TestNewSettingsStates:
    """Tests for SETTINGS_DOWNLOADS and SETTINGS_USERS states"""

    def test_settings_downloads_exists(self):
        assert hasattr(States, "SETTINGS_DOWNLOADS")

    def test_settings_downloads_is_string(self):
        assert isinstance(States.SETTINGS_DOWNLOADS, str)

    def test_settings_users_exists(self):
        assert hasattr(States, "SETTINGS_USERS")

    def test_settings_users_is_string(self):
        assert isinstance(States.SETTINGS_USERS, str)
