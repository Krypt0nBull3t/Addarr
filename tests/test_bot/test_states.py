"""Tests for src/bot/states.py"""

from src.bot.states import States


class TestMediaStates:
    """Tests for media conversation states"""

    def test_media_states_are_integers(self):
        """SEARCHING, SELECTING, QUALITY_SELECT, SEASON_SELECT are all int"""
        assert isinstance(States.SEARCHING, int)
        assert isinstance(States.SELECTING, int)
        assert isinstance(States.QUALITY_SELECT, int)
        assert isinstance(States.SEASON_SELECT, int)

    def test_media_states_unique(self):
        """All 4 media state values are distinct"""
        media_states = [
            States.SEARCHING,
            States.SELECTING,
            States.QUALITY_SELECT,
            States.SEASON_SELECT,
        ]
        assert len(media_states) == len(set(media_states))


class TestAuthStates:
    """Tests for authentication states"""

    def test_password_state(self):
        """PASSWORD == 0"""
        assert States.PASSWORD == 0


class TestGeneralStates:
    """Tests for general states"""

    def test_end_state(self):
        """END == 'end'"""
        assert States.END == "end"


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
