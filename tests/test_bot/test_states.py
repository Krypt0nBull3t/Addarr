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


class TestStringStates:
    """Tests for string-based states"""

    def test_string_states_are_strings(self):
        """AWAITING_DELETE_CONFIRMATION, AWAITING_STATUS_ACTION,
        AWAITING_SETTING_ACTION, AWAITING_SPEED_INPUT are all str"""
        assert isinstance(States.AWAITING_DELETE_CONFIRMATION, str)
        assert isinstance(States.AWAITING_STATUS_ACTION, str)
        assert isinstance(States.AWAITING_SETTING_ACTION, str)
        assert isinstance(States.AWAITING_SPEED_INPUT, str)


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
        ]
        assert len(settings_states) == len(set(settings_states))
