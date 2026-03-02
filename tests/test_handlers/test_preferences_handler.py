"""
Tests for src/bot/handlers/preferences.py - PreferencesHandler.

PreferencesHandler provides /preferences command to view/toggle view mode.
show_preferences shows current mode with toggle button.
handle_toggle switches mode via PreferencesService.
Both methods require authentication via @require_auth.
"""

import pytest


# ---------------------------------------------------------------------------
# /preferences command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_preferences_displays_card_mode(
    preferences_handler, make_update, make_context
):
    """show_preferences shows current card view mode."""
    preferences_handler._mock_prefs.get_view_mode.return_value = "card"

    update = make_update(text="/preferences")
    context = make_context()

    await preferences_handler.show_preferences(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0]
    assert "Card View" in text


@pytest.mark.asyncio
async def test_show_preferences_displays_list_mode(
    preferences_handler, make_update, make_context
):
    """show_preferences shows current list view mode."""
    preferences_handler._mock_prefs.get_view_mode.return_value = "list"

    update = make_update(text="/preferences")
    context = make_context()

    await preferences_handler.show_preferences(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0]
    assert "List View" in text


@pytest.mark.asyncio
async def test_show_preferences_has_toggle_button(
    preferences_handler, make_update, make_context
):
    """show_preferences includes a toggle button."""
    update = make_update(text="/preferences")
    context = make_context()

    await preferences_handler.show_preferences(update, context)

    call_args = update.message.reply_text.call_args
    reply_markup = call_args[1]["reply_markup"]
    all_callbacks = [
        btn.callback_data
        for row in reply_markup.inline_keyboard
        for btn in row
    ]
    assert "pref_toggle_view" in all_callbacks


@pytest.mark.asyncio
async def test_show_preferences_unauthenticated_rejected(
    preferences_handler, make_update, make_context
):
    """Unauthenticated user is rejected by @require_auth."""
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()  # Clear auth

    update = make_update(text="/preferences")
    context = make_context()

    await preferences_handler.show_preferences(update, context)

    # The auth decorator sends the "not authorized" message
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    text = call_args[0][0]
    assert "NotAuthorized" in text or "authenticate" in text.lower()


# ---------------------------------------------------------------------------
# toggle callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_toggle_switches_mode(
    preferences_handler, make_update, make_context
):
    """handle_toggle toggles view mode via PreferencesService."""
    preferences_handler._mock_prefs.toggle_view_mode.return_value = "list"

    update = make_update(callback_data="pref_toggle_view")
    context = make_context()

    await preferences_handler.handle_toggle(update, context)

    preferences_handler._mock_prefs.toggle_view_mode.assert_called_once_with(
        12345
    )


@pytest.mark.asyncio
async def test_handle_toggle_updates_message(
    preferences_handler, make_update, make_context
):
    """handle_toggle edits the message to show new mode."""
    preferences_handler._mock_prefs.toggle_view_mode.return_value = "list"

    update = make_update(callback_data="pref_toggle_view")
    context = make_context()

    await preferences_handler.handle_toggle(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    assert "List View" in text


@pytest.mark.asyncio
async def test_handle_toggle_no_callback_query(
    preferences_handler, make_update, make_context
):
    """handle_toggle returns None when no callback_query."""
    update = make_update(text="test")
    update.callback_query = None
    context = make_context()

    result = await preferences_handler.handle_toggle(update, context)

    assert result is None


def test_get_handler_returns_list(preferences_handler):
    """get_handler returns a list of handlers."""
    handlers = preferences_handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0
