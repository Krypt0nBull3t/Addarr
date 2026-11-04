"""
F063: the "modify" rate limit is checked once, just before each add request.

Picker and toggle taps never use it up: modify allows 5 calls per 60 s, and a
normal album add (result tap, quality tap, album toggles, confirm) would burn it.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SERIES = {"id": "123", "title": "Test Series"}
ARTIST = {"id": "artist-1", "title": "Test Artist"}
SEASONS = [{"seasonNumber": 1}, {"seasonNumber": 2}]


@contextmanager
def modify_limit(max_requests):
    """Turn rate limiting on with a modify limit of max_requests per 60 s."""
    with (
        patch("src.services.rate_limit.TranslationService") as ts_class,
        patch("src.services.rate_limit.config") as cfg,
    ):
        ts_class.return_value.get_text = MagicMock(side_effect=lambda key, **kw: key)
        cfg.get.return_value = {
            "enable": True,
            "limits": {"modify": {"maxRequests": max_requests, "windowSeconds": 60}},
        }
        yield


def _tap(make_update, data):
    update = make_update(callback_data=data)
    update.callback_query.message.photo = None
    update.callback_query.message.reply_markup = MagicMock()
    update.callback_query.message.reply_markup.to_dict.return_value = {}
    return update


# (handler method, callback data, user_data, mocked add method)
ADD_SITES = {
    "quality_movie": (
        "handle_quality_selection", "quality_1",
        {"search_type": "movie", "selected_media": {"id": "1", "title": "Movie"},
         "quality_data": {"root_folder": "/movies"}},
        "add_movie_with_profile",
    ),
    "quality_music_album": (
        "handle_quality_selection", "quality_1",
        {"search_type": "music", "music_type": "album", "album_id": "abc",
         "artist_id": "artist-1", "selected_media": {"id": "album:abc", "title": "A"},
         "quality_data": {"root_folder": "/music"}},
        "add_music_with_profile",
    ),
    "season_confirm": (
        "handle_season_selection", "season_confirm",
        {"selected_media": SERIES, "selected_profile_id": 1,
         "selected_root_folder": "/tv", "selected_seasons": {1},
         "quality_data": {"seasons": SEASONS}},
        "add_series_with_profile",
    ),
    "album_monitor_mode_all": (
        "handle_album_monitor_mode", "album_monitor_mode_all",
        {"selected_media": ARTIST, "selected_profile_id": 1,
         "selected_root_folder": "/music"},
        "add_music_with_profile",
    ),
    "albumsel_monitor_all": (
        "handle_album_selection", "albumsel_monitor_all",
        {"selected_media": ARTIST, "selected_profile_id": 1,
         "selected_root_folder": "/music", "artist_albums": []},
        "add_music_with_profile",
    ),
    "album_confirm": (
        "handle_album_selection", "albumsel_confirm",
        {"selected_media": ARTIST, "selected_profile_id": 1,
         "selected_root_folder": "/music", "selected_albums": {"abc"}},
        "add_music_with_profile",
    ),
}


@pytest.mark.parametrize("site", ADD_SITES)
@pytest.mark.asyncio
async def test_second_add_is_refused_once_modify_limit_is_used_up(
    media_handler, make_update, make_context, site
):
    method, data, user_data, add_name = ADD_SITES[site]
    add = AsyncMock(return_value=(True, "Added"))
    setattr(media_handler._mock_service, add_name, add)
    update = _tap(make_update, data)
    context = make_context(user_data=dict(user_data))
    context.user_data["quality_message_id"] = update.callback_query.message.message_id

    with modify_limit(1):
        await getattr(media_handler, method)(update, context)
        await getattr(media_handler, method)(update, context)

    add.assert_awaited_once()
    update.callback_query.message.reply_text.assert_any_call("RateLimitExceeded")


@pytest.mark.asyncio
async def test_picker_and_toggle_taps_do_not_use_up_the_modify_limit(
    media_handler, make_update, make_context
):
    """Quality tap, season toggles and confirm: only the confirm counts."""
    add = AsyncMock(return_value=(True, "Added"))
    media_handler._mock_service.add_series_with_profile = add
    quality = _tap(make_update, "quality_1")
    context = make_context(user_data={
        "search_type": "series",
        "selected_media": SERIES,
        "quality_message_id": quality.callback_query.message.message_id,
        "quality_data": {"root_folder": "/tv", "seasons": SEASONS},
    })

    with modify_limit(1):
        await media_handler.handle_quality_selection(quality, context)
        for data in ("season_1", "season_2", "season_1", "season_2", "season_1"):
            await media_handler.handle_season_selection(_tap(make_update, data), context)
        await media_handler.handle_season_selection(
            _tap(make_update, "season_confirm"), context
        )

    add.assert_awaited_once()
