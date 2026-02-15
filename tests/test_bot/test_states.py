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
