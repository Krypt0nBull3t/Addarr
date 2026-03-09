"""
Filename: formatters.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Media result display and formatting functions.

Standalone functions extracted from MediaHandler for building captions,
showing search results in card/list views, and editing messages.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.utils.logger import get_logger
from src.services.translation import TranslationService
from src.bot.keyboards import (
    get_search_results_list_keyboard,
    get_list_detail_keyboard,
)

logger = get_logger("addarr.media.formatters")


def build_result_caption(result, index=None, total=None):
    """Build caption text for a search result.

    Args:
        result: Search result dict.
        index: 0-based index (optional, for card view counter).
        total: Total results count (optional, for card view counter).

    Returns:
        Formatted caption string.
    """
    music_type = result.get("music_type")

    # Album-specific caption
    if music_type == "album":
        caption = f"*💿 {result['title']}*\n\n"
        if result.get("artist_name"):
            caption += f"🎤 Artist: {result['artist_name']}\n"
        if result.get("release_date"):
            caption += f"📅 Released: {result['release_date'][:10]}\n"
        if result.get("overview", "No overview available") != "No overview available":
            overview = result["overview"]
            if len(overview) > 300:
                overview = overview[:297] + "..."
            caption += f"\n_{overview}_\n"
        if index is not None and total is not None:
            caption += f"\n📊 Result {index + 1} of {total}"
        return caption

    # Song-specific caption
    if music_type == "song":
        caption = f"*🎵 {result['title']}*\n\n"
        if result.get("album_title"):
            caption += f"💿 Album: {result['album_title']}\n"
        if result.get("artist_name"):
            caption += f"🎤 Artist: {result['artist_name']}\n"
        if index is not None and total is not None:
            caption += f"\n📊 Result {index + 1} of {total}"
        return caption

    overview = result.get('overview', 'No overview available')
    if len(overview) > 300:
        overview = overview[:297] + "..."

    caption = (
        f"*{result['title']}*\n\n"
        f"_{overview}_\n\n"
    )

    if "year" in result:
        caption += f"📅 Year: {result.get('year', 'N/A')}\n"

    if "ratings" in result:
        ratings = result["ratings"]
        if "imdb" in ratings:
            imdb_rating = ratings["imdb"]
            if imdb_rating != "N/A":
                imdb_rating = f"{float(imdb_rating):.1f}/10"
            caption += f"🎭 IMDB: {imdb_rating}\n"

            rt_rating = ratings.get("rottenTomatoes")
            if rt_rating and rt_rating != "N/A":
                rt_rating = f"{rt_rating}%"
                caption += f"🍅 Rotten Tomatoes: {rt_rating}\n"
        elif "tmdb" in ratings:
            tmdb_rating = ratings["tmdb"]
            if tmdb_rating != "N/A":
                rating_value = f"{float(tmdb_rating):.1f}/10"
                votes = ratings.get("votes", 0)
                caption += f"📊 TMDB: {rating_value} ({votes:,} votes)\n"

    if "studio" in result:
        studio = result.get("studio", "N/A")
        if "network" in result:
            network = result.get("network", "N/A")
            if studio and studio != network:
                caption += f"📺 Network: {network} ({studio})\n"
            else:
                caption += f"📺 Network: {network}\n"
        else:
            caption += f"🎬 Studio: {studio}\n"

    if "runtime" in result and result["runtime"] != "N/A":
        caption += f"⏱️ Runtime: {result['runtime']} minutes\n"

    if "genres" in result:
        genres = result.get("genres", [])
        if genres:
            caption += f"🎭 Genres: {', '.join(genres[:3])}"
            if len(genres) > 3:
                caption += f" +{len(genres) - 3} more"
            caption += "\n"

    if index is not None and total is not None:
        caption += f"\n📊 Result {index + 1} of {total}"

    return caption


async def show_result(message, result, index: int, total: int):
    """Show a single search result with navigation buttons (card view)."""
    try:
        caption = build_result_caption(result, index=index, total=total)

        # Create navigation keyboard
        keyboard = []

        nav_buttons = []
        if index > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data=f"nav_prev_{index}")
            )
        if index < total - 1:
            nav_buttons.append(
                InlineKeyboardButton("➡️ Next", callback_data=f"nav_next_{index}")
            )
        if nav_buttons:
            keyboard.append(nav_buttons)

        # Action buttons
        keyboard.extend([
            [InlineKeyboardButton("✅ Add to Library", callback_data=f"select_{result['id']}")],
            [InlineKeyboardButton("📋 Switch to List View", callback_data="viewtoggle")],
            [InlineKeyboardButton("❌ Cancel", callback_data="select_cancel")]
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        poster_url = result.get("poster")

        if poster_url:
            try:
                new_message = await message.reply_photo(
                    photo=poster_url,
                    caption=caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                await message.delete()
                return new_message
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                new_message = await message.reply_text(
                    caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                await message.delete()
                return new_message
        else:
            new_message = await message.reply_text(
                caption,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            await message.delete()
            return new_message

    except Exception as e:
        logger.error(f"Error showing result: {e}")
        try:
            new_message = await message.reply_text(
                TranslationService().get_text("DisplayResultError"),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Cancel", callback_data="select_cancel")
                ]])
            )
            await message.delete()
            return new_message
        except Exception as e2:
            logger.error(f"Error in fallback message: {e2}")
            return message


async def show_list(message, results, page, search_type):
    """Show paginated list view of search results.

    Args:
        message: Telegram message to reply to / delete.
        results: Full list of search results.
        page: Current page (0-indexed).
        search_type: "movie", "series", or "music".
    """
    reply_markup = get_search_results_list_keyboard(
        results, page, page_size=5, search_type=search_type
    )
    header = f"📋 Search results ({len(results)} found):"
    new_message = await message.reply_text(
        header,
        reply_markup=reply_markup
    )
    await message.delete()
    return new_message


async def show_list_detail(message, result):
    """Show detail view for a single result from list view.

    Args:
        message: Telegram message to reply to / delete.
        result: The selected search result dict.
    """
    caption = build_result_caption(result)
    reply_markup = get_list_detail_keyboard(result["id"])
    poster_url = result.get("poster")

    if poster_url:
        try:
            new_message = await message.reply_photo(
                photo=poster_url,
                caption=caption,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            await message.delete()
            return new_message
        except Exception as e:
            logger.error(f"Error sending photo in list detail: {e}")
            new_message = await message.reply_text(
                caption,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            await message.delete()
            return new_message
    else:
        new_message = await message.reply_text(
            caption,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await message.delete()
        return new_message


async def send_response(message, text: str, reply_markup=None):
    """Send or edit a message based on message type."""
    try:
        if message.photo:
            await message.edit_caption(
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await message.edit_text(
                text=text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        # Fallback: send new message
        await message.reply_text(text, reply_markup=reply_markup)
