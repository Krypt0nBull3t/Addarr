"""
Integration tests for the /webhooks wizard.

Drives the real handler chain: menu, show the stored secret, Back, the port
prompt with Cancel, and the private-chat rule.
"""

import json

import pytest
from telegram import Update
from unittest.mock import patch

from src.bot.states import States
from tests.conftest import MockConfig
from tests.integration.conftest import make_command_update

CONVERSATION = "webhooks_conversation"


def _buttons(response):
    """callback_data of every inline button of a captured response."""
    markup = response.reply_markup
    if isinstance(markup, str):  # PTB sends reply_markup as a JSON string
        markup = json.loads(markup)
    keyboard = markup["inline_keyboard"]
    return [button["callback_data"] for row in keyboard for button in row]


@pytest.fixture
def webhook_config():
    """Admin 12345, webhooks on, a Radarr secret stored, group chats allowed."""
    cfg = MockConfig()
    cfg._set("admins", [12345])
    cfg._set("security", {
        "enableAdmin": True, "enableAllowlist": False, "chatMode": "allow_all",
    })
    cfg._set("webhooks", {
        "enable": True,
        "port": 8080,
        "host": "127.0.0.1",
        "radarr_secret": "stored-radarr-secret",
        "sonarr_secret": None,
        "lidarr_secret": None,
        "events": {"grab": True},
    })
    with (
        patch("src.bot.handlers.webhooks.config", cfg),
        patch("src.bot.handlers.auth.config", cfg),
        patch("src.utils.helpers.config", cfg),
    ):
        yield cfg


@pytest.mark.asyncio
async def test_menu_existing_secret_and_back(harness, webhook_config):
    """Tapping a set-up service keeps its secret; Back returns to the menu."""
    resp = await harness.send_command("/webhooks")
    assert "wh_setup_radarr" in _buttons(resp)

    resp = await harness.tap_button("wh_setup_radarr")
    assert "wh_regen_radarr" in _buttons(resp)
    assert webhook_config.get("webhooks")["radarr_secret"] == "stored-radarr-secret"

    resp = await harness.tap_button("wh_back")
    assert resp.method == "editMessageText"
    assert "wh_setup_radarr" in _buttons(resp)
    assert harness.get_conversation_state(CONVERSATION) == States.WEBHOOK_MENU


@pytest.mark.asyncio
async def test_port_prompt_cancel_ends_conversation(harness, webhook_config):
    """Cancel on the port prompt ends the flow; later text is not saved as a port."""
    await harness.send_command("/webhooks")
    resp = await harness.tap_button("wh_port")
    assert _buttons(resp) == ["menu_cancel"]
    assert harness.get_conversation_state(CONVERSATION) == States.WEBHOOK_CHANGE_PORT

    await harness.tap_button("menu_cancel")
    assert harness.get_conversation_state(CONVERSATION) is None

    await harness.send_text("9090")
    assert webhook_config.get("webhooks")["port"] == 8080


@pytest.mark.asyncio
async def test_group_chat_is_refused(harness, webhook_config):
    """/webhooks in a group sends no menu and no secret, even with allow_all."""
    data = make_command_update("/webhooks")
    data["message"]["chat"]["type"] = "group"
    data["message"]["chat"]["title"] = "Family"

    await harness.app.process_update(Update.de_json(data, harness.app.bot))

    assert harness.responses
    assert all("stored-radarr-secret" not in r.text for r in harness.responses)
    assert all(r.reply_markup is None for r in harness.responses)
    assert harness.get_conversation_state(CONVERSATION) is None
