"""
Integration test infrastructure.

BotHarness builds a real PTB Application with all handlers registered,
processes Update objects through the handler chain, and captures bot
responses by intercepting HTTPXRequest.do_request — no Telegram connection needed.
"""

import json as json_mod
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import patch

import pytest
from aioresponses import aioresponses
from telegram import Update
from telegram.ext import Application, ConversationHandler

from src.bot.handlers.auth import AuthHandler
from src.bot.handlers.start import StartHandler
from src.bot.handlers.media import MediaHandler
from src.bot.handlers.help import HelpHandler
from src.bot.handlers.system import SystemHandler
from src.bot.handlers.settings import SettingsHandler
from src.bot.handlers.webhooks import WebhooksHandler
from src.bot.handlers.delete import DeleteHandler
from src.bot.handlers.library import LibraryHandler
from src.bot.handlers.calendar import CalendarHandler
from src.bot.handlers.missing import MissingHandler
from src.bot.handlers.queue import QueueHandler
from src.bot.handlers.history import HistoryHandler
from src.bot.handlers.downloads import DownloadsHandler
from src.bot.handlers.preferences import PreferencesHandler
from src.bot.handlers.bazarr import BazarrHandler
from src.config.settings import config
from src.services.transmission import TransmissionService
from src.services.sabnzbd import SABnzbdService
from src.services.bazarr import BazarrService


# ---- Response capture -------------------------------------------------------

@dataclass
class BotResponse:
    """A captured outgoing bot API call."""
    method: str
    text: str = ""
    chat_id: int = 0
    reply_markup: Optional[dict] = None
    photo: Optional[str] = None
    raw: dict = field(default_factory=dict)


def _extract_response(endpoint: str, data: dict) -> BotResponse:
    """Convert a raw _do_post call into a BotResponse."""
    text = data.get("text", "") or data.get("caption", "")
    chat_id = data.get("chat_id", 0)
    reply_markup = data.get("reply_markup")
    photo = data.get("photo")
    return BotResponse(
        method=endpoint,
        text=str(text),
        chat_id=int(chat_id) if chat_id else 0,
        reply_markup=reply_markup,
        photo=photo,
        raw=data,
    )


# Minimal fake API results keyed by endpoint.
# _do_post must return dicts that PTB can parse into objects.
_FAKE_RESULTS = {
    "getMe": {
        "id": 999,
        "is_bot": True,
        "first_name": "AddarrTestBot",
        "username": "addarr_test_bot",
    },
    "sendMessage": {
        "message_id": 100,
        "date": 0,
        "chat": {"id": 12345, "type": "private"},
        "text": "",
    },
    "editMessageText": {
        "message_id": 100,
        "date": 0,
        "chat": {"id": 12345, "type": "private"},
        "text": "",
    },
    "editMessageCaption": {
        "message_id": 100,
        "date": 0,
        "chat": {"id": 12345, "type": "private"},
    },
    "editMessageReplyMarkup": {
        "message_id": 100,
        "date": 0,
        "chat": {"id": 12345, "type": "private"},
    },
    "sendPhoto": {
        "message_id": 100,
        "date": 0,
        "chat": {"id": 12345, "type": "private"},
    },
    "deleteMessage": True,
    "answerCallbackQuery": True,
}


# ---- Update factories -------------------------------------------------------

_update_counter = 0


def _reset_update_counter():
    global _update_counter
    _update_counter = 0


def _next_update_id():
    global _update_counter
    _update_counter += 1
    return _update_counter


def make_command_update(command: str, user_id: int = 12345, chat_id: int = 12345):
    """Build a real Update for a /command message."""
    text = command if command.startswith("/") else f"/{command}"
    return {
        "update_id": _next_update_id(),
        "message": {
            "message_id": _next_update_id(),
            "date": 0,
            "chat": {"id": chat_id, "type": "private"},
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
            },
            "text": text,
            "entities": [
                {"type": "bot_command", "offset": 0, "length": len(text.split()[0])}
            ],
        },
    }


def make_text_update(text: str, user_id: int = 12345, chat_id: int = 12345):
    """Build a real Update for a plain text message."""
    return {
        "update_id": _next_update_id(),
        "message": {
            "message_id": _next_update_id(),
            "date": 0,
            "chat": {"id": chat_id, "type": "private"},
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
            },
            "text": text,
        },
    }


def make_callback_update(
    callback_data: str,
    user_id: int = 12345,
    chat_id: int = 12345,
    message_id: int = 100,
):
    """Build a real Update for a callback query (inline button tap)."""
    return {
        "update_id": _next_update_id(),
        "callback_query": {
            "id": str(_next_update_id()),
            "chat_instance": "test",
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
            },
            "data": callback_data,
            "message": {
                "message_id": message_id,
                "date": 0,
                "chat": {"id": chat_id, "type": "private"},
                "from": {
                    "id": 0,
                    "is_bot": True,
                    "first_name": "AddarrBot",
                },
                "text": "previous message",
            },
        },
    }


# ---- BotHarness -------------------------------------------------------------

class BotHarness:
    """Drives a real PTB Application with all handlers, no Telegram connection.

    Intercepts HTTPXRequest.do_request to capture outgoing API calls and
    return plausible fake results so PTB's internals don't break.
    """

    def __init__(self, app: Application):
        self.app = app
        self.responses: list[BotResponse] = []
        self._last_message_id = 100

    @property
    def last_response(self) -> Optional[BotResponse]:
        return self.responses[-1] if self.responses else None

    def _next_message_id(self) -> int:
        self._last_message_id += 1
        return self._last_message_id

    async def _fake_do_request(self, url, method, request_data=None, **kwargs):
        """Intercept HTTPXRequest.do_request — the lowest network layer.

        Returns (status_code, response_bytes) in Telegram Bot API format:
        {"ok": true, "result": <payload>}
        """
        # Extract endpoint name from URL (e.g., ".../bot0:TEST/sendMessage")
        endpoint = url.rsplit("/", 1)[-1] if "/" in url else url

        # Extract parameters from request_data
        data = {}
        if request_data and request_data.json_parameters:
            data = dict(request_data.json_parameters)

        # Don't capture internal calls like getMe
        if endpoint not in ("getMe",):
            self.responses.append(_extract_response(endpoint, data))

        # Build a plausible result
        result = _FAKE_RESULTS.get(endpoint)
        if isinstance(result, dict):
            result = dict(result)
            result["message_id"] = self._next_message_id()
            if "text" in data:
                result["text"] = data["text"]
            if "caption" in data:
                result["caption"] = data["caption"]
        elif result is None:
            result = True

        payload = json_mod.dumps({"ok": True, "result": result}).encode()
        return 200, payload

    def _clear(self):
        """Clear captured responses for the next interaction step."""
        self.responses.clear()

    async def send_command(self, command: str, user_id: int = 12345) -> Optional[BotResponse]:
        """Simulate user sending a /command."""
        self._clear()
        update_data = make_command_update(command, user_id=user_id)
        update = Update.de_json(update_data, self.app.bot)
        await self.app.process_update(update)
        return self.last_response

    async def send_text(self, text: str, user_id: int = 12345) -> Optional[BotResponse]:
        """Simulate user typing a plain text message."""
        self._clear()
        update_data = make_text_update(text, user_id=user_id)
        update = Update.de_json(update_data, self.app.bot)
        await self.app.process_update(update)
        return self.last_response

    def get_conversation_state(
        self, handler_name: str, chat_id: int = 12345, user_id: int = 12345
    ) -> Optional[int]:
        """Get the current state of a named ConversationHandler.

        Returns the state integer (e.g. SEARCHING=1) or None if not in conversation.
        """
        for group_handlers in self.app.handlers.values():
            for handler in group_handlers:
                if (
                    isinstance(handler, ConversationHandler)
                    and handler.name == handler_name
                ):
                    key = (chat_id, user_id)
                    conversations = handler._conversations
                    if key in conversations:
                        # PTB stores state as a tuple: (state,) or just state
                        state = conversations[key]
                        if isinstance(state, tuple):
                            return state[0]
                        return state
                    return None
        return None

    async def tap_button(
        self, callback_data: str, user_id: int = 12345, message_id: int = 100
    ) -> Optional[BotResponse]:
        """Simulate user tapping an inline keyboard button."""
        self._clear()
        update_data = make_callback_update(
            callback_data, user_id=user_id, message_id=message_id
        )
        update = Update.de_json(update_data, self.app.bot)
        await self.app.process_update(update)
        return self.last_response


# ---- Application builder ----------------------------------------------------

def _register_handlers(app: Application):
    """Register handlers in the same order as AddarrBot._add_handlers()."""
    handler_classes = [
        StartHandler,
        AuthHandler,
        MediaHandler,
        SettingsHandler,
        WebhooksHandler,
        DeleteHandler,
        LibraryHandler,
        CalendarHandler,
        MissingHandler,
        QueueHandler,
        HistoryHandler,
    ]

    # Conditionally add download handlers
    if config.get("transmission", {}).get("enable", False):
        from src.bot.handlers.transmission import TransmissionHandler
        handler_classes.append(TransmissionHandler)

    if config.get("sabnzbd", {}).get("enable", False):
        from src.bot.handlers.sabnzbd import SabnzbdHandler
        handler_classes.append(SabnzbdHandler)

    # Bazarr handler (if enabled)
    if config.get("bazarr", {}).get("enable", False):
        handler_classes.append(BazarrHandler)

    # Downloads handler checks is_enabled internally
    handler_classes.append(DownloadsHandler)

    # These come after downloads in main.py
    handler_classes.extend([HelpHandler, PreferencesHandler, SystemHandler])

    for cls in handler_classes:
        instance = cls()
        for handler in instance.get_handler():
            app.add_handler(handler)


def _build_application() -> Application:
    """Build a real Application with handlers (not yet initialized)."""
    app = Application.builder().token("0:TEST").build()
    _register_handlers(app)
    return app


# ---- Fixtures ----------------------------------------------------------------

@pytest.fixture
def aio_mock():
    """Provide aioresponses mock for async HTTP requests."""
    with aioresponses() as m:
        yield m


async def _make_harness(app):
    """Shared helper: patch transport, initialize, yield, shutdown."""
    _reset_update_counter()
    h = BotHarness(app)

    with patch(
        "telegram.request.HTTPXRequest.do_request",
        side_effect=h._fake_do_request,
    ):
        await app.initialize()
        yield h
        await app.shutdown()


@pytest.fixture
async def harness():
    """Provide a BotHarness with a fully wired Application."""
    AuthHandler._authenticated_users.add(12345)
    app = _build_application()
    async for h in _make_harness(app):
        yield h


@pytest.fixture
async def downloads_harness():
    """Provide a BotHarness with downloads handlers enabled."""
    AuthHandler._authenticated_users.add(12345)

    with (
        patch.object(TransmissionService, "is_enabled", return_value=True),
        patch.object(SABnzbdService, "is_enabled", return_value=True),
    ):
        app = _build_application()
        async for h in _make_harness(app):
            yield h


@pytest.fixture
async def bazarr_harness():
    """Provide a BotHarness with BazarrHandler enabled."""
    AuthHandler._authenticated_users.add(12345)

    with patch.object(BazarrService, "is_enabled", return_value=True):
        app = Application.builder().token("0:TEST").build()
        # Capture the real get before patching
        real_get = config.get.__wrapped__ if hasattr(config.get, "__wrapped__") else config.get

        def _get_with_bazarr(key, default=None):
            if key == "bazarr":
                return {"enable": True}
            return real_get(key, default)

        with patch.object(config, "get", side_effect=_get_with_bazarr):
            _register_handlers(app)

        async for h in _make_harness(app):
            yield h
