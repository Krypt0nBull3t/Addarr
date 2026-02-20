"""
Root conftest.py -- Mock config injection and shared fixtures.

CRITICAL: The sys.modules injection MUST happen before any src.* imports.
src/config/settings.py line 138 runs `config = Config()` at module level,
which reads config.yaml from disk. We intercept this by injecting a mock
module into sys.modules so all `from src.config.settings import config`
statements get our mock instead.
"""

import os
import sys
import types
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Mock config -- injected into sys.modules BEFORE any src imports
# ---------------------------------------------------------------------------

MOCK_CONFIG_DATA = {
    "telegram": {"token": "test-token", "password": "test-pass"},
    "radarr": {
        "enable": True,
        "server": {"addr": "localhost", "port": 7878, "path": "/", "ssl": False},
        "auth": {"apikey": "test-radarr-key", "username": None, "password": None},
        "features": {"search": True, "minimumAvailability": "announced"},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
    },
    "sonarr": {
        "enable": True,
        "server": {"addr": "localhost", "port": 8989, "path": "/", "ssl": False},
        "auth": {"apikey": "test-sonarr-key", "username": None, "password": None},
        "features": {"search": True, "seasonFolder": True},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
    },
    "lidarr": {
        "enable": True,
        "server": {"addr": "localhost", "port": 8686, "path": "/", "ssl": False},
        "auth": {"apikey": "test-lidarr-key", "username": None, "password": None},
        "features": {"search": True, "albumFolder": True, "monitorOption": "all"},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
        "metadataProfileId": 1,
    },
    "transmission": {
        "enable": False, "onlyAdmin": True, "host": "localhost",
        "port": 9091, "ssl": False,
        "authentication": False, "username": None, "password": None,
    },
    "sabnzbd": {
        "enable": False, "onlyAdmin": True,
        "server": {"addr": "localhost", "port": 8090, "path": "/", "ssl": False},
        "auth": {"apikey": "test-sabnzbd-key"},
    },
    "entrypoints": {
        "auth": "auth", "help": "help", "add": "start",
        "allSeries": "allSeries", "allMovies": "allMovies", "allMusic": "allMusic",
        "transmission": "transmission", "sabnzbd": "sabnzbd",
    },
    "security": {"enableAdmin": False, "enableAllowlist": False},
    "language": "en-us",
    "logging": {"toConsole": False, "debug": False, "adminNotifyId": None},
    "admins": [], "allow_list": [], "chat_id": [],
    "authenticated_users": [12345],
    "enableAllowlist": False, "logToConsole": False, "debugLogging": False,
}


class MockConfig:
    """Mock Config class that mimics src.config.settings.Config API."""

    def __init__(self, data=None):
        self._config = deepcopy(data or MOCK_CONFIG_DATA)

    def __getitem__(self, key):
        return self._config[key]

    def get(self, key, default=None):
        return self._config.get(key, default)

    def _set(self, key, value):
        """Test helper to override a config value."""
        self._config[key] = value

    def update_nested(self, dotted_key, value):
        """Update a nested config value using dot notation."""
        keys = dotted_key.split(".")
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def save(self):
        """No-op in tests."""
        pass


# Create the mock config instance
_mock_config = MockConfig()

# Create a fake settings module and inject it BEFORE any src imports
_settings_mod = types.ModuleType("src.config.settings")
_settings_mod.config = _mock_config
_settings_mod.Config = MockConfig
_settings_mod.ConfigurationError = type("ConfigurationError", (Exception,), {})
_ConfigurationError = _settings_mod.ConfigurationError


def _validate_port(port, service_name):
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise _ConfigurationError(
            f"Invalid port for {service_name}: {port}. Must be between 1 and 65535."
        )


def _validate_service_apikey(service_config, service_name):
    if service_config.get("enable"):
        apikey = service_config.get("auth", {}).get("apikey")
        if not apikey or not str(apikey).strip():
            raise _ConfigurationError(
                f"{service_name} is enabled but has no API key configured."
            )


def _validate_telegram_token(telegram_config):
    if not telegram_config.get("token"):
        raise _ConfigurationError(
            "Telegram bot token is not configured."
        )


def _validate_server_addr(addr, service_name):
    if not addr or not str(addr).strip():
        raise _ConfigurationError(
            f"Invalid server address for {service_name}: address is empty."
        )
    addr_str = str(addr)
    if addr_str.startswith(("http://", "https://")):
        raise _ConfigurationError(
            f"Invalid server address for {service_name}: '{addr_str}'. "
            f"Remove the protocol prefix (http:// or https://). "
            f"Use the 'ssl' option instead."
        )
    if " " in addr_str.strip():
        raise _ConfigurationError(
            f"Invalid server address for {service_name}: '{addr_str}'. "
            f"Address must not contain spaces."
        )


_settings_mod.validate_port = _validate_port
_settings_mod.validate_service_apikey = _validate_service_apikey
_settings_mod.validate_telegram_token = _validate_telegram_token
_settings_mod.validate_server_addr = _validate_server_addr
sys.modules["src.config.settings"] = _settings_mod

# Also inject the parent packages so Python doesn't try to import them
# and trigger the real Config() instantiation.
# IMPORTANT: The fake modules must have __path__ set so Python treats them
# as packages and can still discover sub-packages (e.g. src.bot, src.models).
_src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if "src" not in sys.modules:
    _src_mod = types.ModuleType("src")
    _src_mod.__path__ = [_src_dir]
    sys.modules["src"] = _src_mod
if "src.config" not in sys.modules:
    _config_mod = types.ModuleType("src.config")
    _config_mod.__path__ = [os.path.join(_src_dir, "config")]
    _config_mod.settings = _settings_mod
    sys.modules["src.config"] = _config_mod

# ---------------------------------------------------------------------------
# 2. Singleton reset fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singleton instances between tests to prevent state leakage."""
    yield

    # Import here (after sys.modules injection) to avoid triggering real config
    from src.services.media import MediaService
    from src.services.health import HealthService
    from src.services.translation import TranslationService
    from src.services.notification import NotificationService
    from src.bot.handlers.auth import AuthHandler

    # Reset singletons
    MediaService._instance = None
    MediaService._radarr = None
    MediaService._sonarr = None
    MediaService._lidarr = None

    HealthService._instance = None

    TranslationService._instance = None
    TranslationService._translations = {}

    NotificationService._instance = None
    NotificationService._bot = None

    AuthHandler._authenticated_users = set()


# ---------------------------------------------------------------------------
# 3. Mock config fixture (provides fresh copy per test)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    """Provide a fresh MockConfig for tests that need to override values."""
    return MockConfig()


# ---------------------------------------------------------------------------
# 4. Translation mock fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_translation():
    """Mock TranslationService to return keys as text (identity function)."""
    with patch("src.services.translation.TranslationService._load_translations"):
        yield


# ---------------------------------------------------------------------------
# 5. Telegram mock factories
# ---------------------------------------------------------------------------


@pytest.fixture
def make_user():
    """Factory fixture for creating mock Telegram User objects."""
    def _make_user(user_id=12345, username="testuser",
                   first_name="Test", last_name="User",
                   is_bot=False):
        user = MagicMock()
        user.id = user_id
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.is_bot = is_bot
        return user
    return _make_user


@pytest.fixture
def make_message(make_user):
    """Factory fixture for creating mock Telegram Message objects."""
    def _make_message(text="test", user=None, chat_id=12345, chat_title=None):
        message = AsyncMock()
        message.text = text
        message.photo = None

        # User
        message.from_user = user or make_user()

        # Chat
        chat = MagicMock()
        chat.id = chat_id
        chat.title = chat_title
        chat.type = "private" if chat_title is None else "group"
        chat.send_message = AsyncMock()
        message.chat = chat

        # Methods
        message.reply_text = AsyncMock()
        message.edit_text = AsyncMock()
        message.edit_caption = AsyncMock()
        message.delete = AsyncMock()

        return message
    return _make_message


@pytest.fixture
def make_callback_query(make_user, make_message):
    """Factory fixture for creating mock Telegram CallbackQuery objects."""
    def _make_callback_query(data="test", user=None, message=None):
        query = AsyncMock()
        query.data = data
        query.from_user = user or make_user()
        query.message = message or make_message()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_caption = AsyncMock()
        return query
    return _make_callback_query


@pytest.fixture
def make_update(make_user, make_message, make_callback_query):
    """Factory fixture for creating mock Telegram Update objects."""
    def _make_update(text=None, callback_data=None, user=None):
        update = MagicMock()
        _user = user or make_user()
        update.effective_user = _user

        if callback_data is not None:
            # Callback query update
            msg = make_message(user=_user)
            query = make_callback_query(data=callback_data, user=_user,
                                        message=msg)
            update.callback_query = query
            update.message = None
            update.effective_message = msg
        else:
            # Text message update
            msg = make_message(text=text or "test", user=_user)
            update.message = msg
            update.callback_query = None
            update.effective_message = msg
            update.effective_chat = msg.chat

        return update
    return _make_update


@pytest.fixture
def make_context():
    """Factory fixture for creating mock Telegram Context objects."""
    def _make_context(user_data=None):
        context = MagicMock()
        context.user_data = user_data if user_data is not None else {}
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        return context
    return _make_context
