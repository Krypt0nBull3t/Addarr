"""
Filename: settings.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Settings handler module.

This module handles bot settings management — language selection,
service enable/disable, and default quality profile configuration.
Admin-only access.
"""

from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
)

from src.config.settings import config
from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_settings_keyboard,
    get_language_keyboard,
    get_quality_profile_keyboard,
    get_downloads_keyboard,
    get_transmission_settings_keyboard,
    get_sabnzbd_settings_keyboard,
    get_users_keyboard,
)
from src.bot.states import States
from src.services.media import MediaService
from src.services.transmission import TransmissionService
from src.services.sabnzbd import SABnzbdService
from src.services.translation import TranslationService
from src.definitions import is_admin

logger = get_logger("addarr.settings")


class SettingsHandler:
    """Handler for settings management (admin-only)"""

    def __init__(self):
        self.translation = TranslationService()
        self.media_service = MediaService()
        self.transmission_service = TransmissionService()
        try:
            self.sabnzbd_service = SABnzbdService()
        except ValueError:
            self.sabnzbd_service = None

    def get_handler(self):
        """Get command handlers for settings operations"""
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler("settings", self.handle_settings),
                    CallbackQueryHandler(
                        self.handle_settings,
                        pattern="^menu_settings$"
                    ),
                ],
                states={
                    States.SETTINGS_MENU: [
                        CallbackQueryHandler(
                            self.handle_language_menu,
                            pattern="^settings_language$"
                        ),
                        CallbackQueryHandler(
                            self.handle_service_menu,
                            pattern="^settings_(radarr|sonarr|lidarr)$"
                        ),
                        CallbackQueryHandler(
                            self.handle_downloads_menu,
                            pattern="^settings_downloads$"
                        ),
                        CallbackQueryHandler(
                            self.handle_users_menu,
                            pattern="^settings_users$"
                        ),
                        CallbackQueryHandler(
                            self.handle_back,
                            pattern="^settings_back$"
                        ),
                    ],
                    States.SETTINGS_LANGUAGE: [
                        CallbackQueryHandler(
                            self.handle_language_select,
                            pattern="^lang_"
                        ),
                        CallbackQueryHandler(
                            self.handle_settings_from_callback,
                            pattern="^settings_back$"
                        ),
                    ],
                    States.SETTINGS_SERVICE: [
                        CallbackQueryHandler(
                            self.handle_service_toggle,
                            pattern="^svc_toggle_"
                        ),
                        CallbackQueryHandler(
                            self.handle_quality_menu,
                            pattern="^svc_quality_"
                        ),
                        CallbackQueryHandler(
                            self.handle_settings_from_callback,
                            pattern="^settings_back$"
                        ),
                    ],
                    States.SETTINGS_QUALITY: [
                        CallbackQueryHandler(
                            self.handle_quality_select,
                            pattern="^setquality_"
                        ),
                        CallbackQueryHandler(
                            self.handle_settings_from_callback,
                            pattern="^settings_back$"
                        ),
                    ],
                    States.SETTINGS_DOWNLOADS: [
                        CallbackQueryHandler(
                            self.handle_transmission_settings,
                            pattern="^dl_transmission$"
                        ),
                        CallbackQueryHandler(
                            self.handle_sabnzbd_settings,
                            pattern="^dl_sabnzbd$"
                        ),
                        CallbackQueryHandler(
                            self.handle_transmission_toggle,
                            pattern="^dl_trans_toggle$"
                        ),
                        CallbackQueryHandler(
                            self.handle_transmission_turtle,
                            pattern="^dl_trans_turtle$"
                        ),
                        CallbackQueryHandler(
                            self.handle_sabnzbd_toggle,
                            pattern="^dl_sab_toggle$"
                        ),
                        CallbackQueryHandler(
                            self.handle_sabnzbd_speed,
                            pattern="^dl_sab_speed"
                        ),
                        CallbackQueryHandler(
                            self.handle_sabnzbd_pause_resume,
                            pattern="^dl_sab_(pause|resume)$"
                        ),
                        CallbackQueryHandler(
                            self.handle_settings_from_callback,
                            pattern="^dl_back$"
                        ),
                    ],
                    States.SETTINGS_USERS: [
                        CallbackQueryHandler(
                            self.handle_users_toggle,
                            pattern="^usr_toggle_"
                        ),
                        CallbackQueryHandler(
                            self.handle_settings_from_callback,
                            pattern="^usr_back$"
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.handle_cancel),
                    CallbackQueryHandler(
                        self.handle_cancel,
                        pattern="^menu_cancel$"
                    ),
                ],
                name="settings_conversation",
                persistent=False,
                per_message=False,
            )
        ]

    @require_auth
    async def handle_settings(self, update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
        """Entry point for settings — admin check + show settings menu"""
        user = update.effective_user
        log_user_interaction(logger, user, "/settings")

        if not is_admin(user.id):
            text = self.translation.get_text(
                "Settings.AdminOnly",
                default="Settings are only available to admins."
            )
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.edit_text(text)
            elif update.message:
                await update.message.reply_text(text)
            return ConversationHandler.END

        text = self.translation.get_text(
            "Settings.Menu", default="Settings"
        )
        keyboard = get_settings_keyboard()

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text(
                f"⚙️ {text}", reply_markup=keyboard
            )
        elif update.message:
            await update.message.reply_text(
                f"⚙️ {text}", reply_markup=keyboard
            )

        return States.SETTINGS_MENU

    async def handle_settings_from_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Return to settings menu from a sub-menu (callback only)"""
        query = update.callback_query
        await query.answer()

        text = self.translation.get_text(
            "Settings.Menu", default="Settings"
        )
        await query.message.edit_text(
            f"⚙️ {text}", reply_markup=get_settings_keyboard()
        )
        return States.SETTINGS_MENU

    # -- Language flow --

    async def handle_language_menu(self, update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
        """Show language selection keyboard"""
        query = update.callback_query
        await query.answer()

        text = self.translation.get_text(
            "Settings.Language", default="Language"
        )
        await query.message.edit_text(
            f"🌐 {text}", reply_markup=get_language_keyboard()
        )
        return States.SETTINGS_LANGUAGE

    async def handle_language_select(self, update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
        """Handle language selection"""
        query = update.callback_query
        await query.answer()

        lang = query.data.replace("lang_", "")

        config.update_nested("language", lang)
        config.save()

        # Update the TranslationService language
        TranslationService._current_language = lang

        text = self.translation.get_text(
            "Settings.LanguageChanged",
            default=f"Language changed to {lang}",
            language=lang,
        )
        await query.message.edit_text(
            f"✅ {text}", reply_markup=get_settings_keyboard()
        )
        return States.SETTINGS_MENU

    # -- Service enable/disable flow --

    async def handle_service_menu(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
        """Show service settings (toggle + quality profile)"""
        query = update.callback_query
        await query.answer()

        service = query.data.replace("settings_", "")
        context.user_data["settings_service"] = service

        service_cfg = config.get(service, {})
        enabled = service_cfg.get("enable", False)
        has_apikey = bool(
            service_cfg.get("auth", {}).get("apikey")
        )

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []

        # Toggle button
        status = "✅ Enabled" if enabled else "❌ Disabled"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} — tap to toggle",
                callback_data=f"svc_toggle_{service}"
            )
        ])

        # Quality profile button (only if service has an API key)
        if has_apikey:
            keyboard.append([
                InlineKeyboardButton(
                    "🎯 Default Quality Profile",
                    callback_data=f"svc_quality_{service}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                f"◀️ {self.translation.get_text('Back')}",
                callback_data="settings_back"
            )
        ])

        await query.message.edit_text(
            f"⚙️ {service.title()} Settings",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return States.SETTINGS_SERVICE

    async def handle_service_toggle(self, update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
        """Toggle a service's enable flag"""
        query = update.callback_query
        await query.answer()

        service = query.data.replace("svc_toggle_", "")
        current = config.get(service, {}).get("enable", False)
        new_value = not current

        config.update_nested(f"{service}.enable", new_value)
        config.save()

        if new_value:
            text = self.translation.get_text(
                "Settings.ServiceEnabled",
                default=f"enabled {service}",
                service=service,
            )
        else:
            text = self.translation.get_text(
                "Settings.ServiceDisabled",
                default=f"disabled {service}",
                service=service,
            )

        await query.message.edit_text(
            f"✅ {text}", reply_markup=get_settings_keyboard()
        )
        return States.SETTINGS_MENU

    # -- Quality profile flow --

    async def handle_quality_menu(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
        """Fetch and show quality profiles for a service"""
        query = update.callback_query
        await query.answer()

        service = query.data.replace("svc_quality_", "")
        context.user_data["settings_service"] = service

        try:
            if service == "radarr":
                profiles = await self.media_service.radarr.get_quality_profiles()
            elif service == "sonarr":
                profiles = await self.media_service.sonarr.get_quality_profiles()
            elif service == "lidarr":
                profiles = await self.media_service.lidarr.get_quality_profiles()
            else:
                profiles = []

            if not profiles:
                text = self.translation.get_text(
                    "Settings.NoProfiles",
                    default=f"No quality profiles found for {service}",
                    service=service,
                )
                await query.message.edit_text(
                    f"❌ {text}", reply_markup=get_settings_keyboard()
                )
                return States.SETTINGS_MENU

            keyboard = get_quality_profile_keyboard(profiles, service)
            await query.message.edit_text(
                f"🎯 Select default quality profile for {service.title()}:",
                reply_markup=keyboard,
            )
            return States.SETTINGS_QUALITY

        except Exception as e:
            logger.error(f"Error fetching quality profiles for {service}: {e}")
            await query.message.edit_text(
                f"❌ Error fetching profiles for {service.title()}.",
                reply_markup=get_settings_keyboard(),
            )
            return States.SETTINGS_MENU

    async def handle_quality_select(self, update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
        """Save selected quality profile"""
        query = update.callback_query
        await query.answer()

        # Parse: setquality_{service}_{id}
        parts = query.data.split("_")
        service = parts[1]
        profile_id = int(parts[2])

        config.update_nested(
            f"{service}.quality.defaultProfileId", profile_id
        )
        config.save()

        text = self.translation.get_text(
            "Settings.QualityProfileSet",
            default=f"Default quality profile set to {profile_id} for {service}",
            profile=str(profile_id),
            service=service,
        )
        await query.message.edit_text(
            f"✅ {text}", reply_markup=get_settings_keyboard()
        )
        return States.SETTINGS_MENU

    # -- Downloads flow --

    async def handle_downloads_menu(self, update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
        """Show downloads sub-menu keyboard"""
        query = update.callback_query
        await query.answer()

        trans_enabled = config.get("transmission", {}).get("enable", False)
        sab_enabled = config.get("sabnzbd", {}).get("enable", False)

        keyboard = get_downloads_keyboard(trans_enabled, sab_enabled)
        await query.message.edit_text(
            "📥 Downloads", reply_markup=keyboard
        )
        return States.SETTINGS_DOWNLOADS

    async def handle_transmission_settings(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show Transmission settings keyboard"""
        query = update.callback_query
        await query.answer()

        enabled = config.get("transmission", {}).get("enable", False)
        status = await self.transmission_service.get_status()
        alt_speed = status.get("alt_speed_enabled", False)

        keyboard = get_transmission_settings_keyboard(enabled, alt_speed)
        await query.message.edit_text(
            "📡 Transmission Settings", reply_markup=keyboard
        )
        return States.SETTINGS_DOWNLOADS

    async def handle_transmission_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Toggle transmission.enable in config"""
        query = update.callback_query
        await query.answer()

        current = config.get("transmission", {}).get("enable", False)
        new_value = not current
        config.update_nested("transmission.enable", new_value)
        config.save()

        status = "enabled" if new_value else "disabled"
        enabled = config.get("transmission", {}).get("enable", False)
        trans_status = await self.transmission_service.get_status()
        alt_speed = trans_status.get("alt_speed_enabled", False)

        keyboard = get_transmission_settings_keyboard(enabled, alt_speed)
        await query.message.edit_text(
            f"✅ Transmission {status}",
            reply_markup=keyboard,
        )
        return States.SETTINGS_DOWNLOADS

    async def handle_transmission_turtle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Toggle Transmission turtle mode via service"""
        query = update.callback_query
        await query.answer()

        status = await self.transmission_service.get_status()
        current = status.get("alt_speed_enabled", False)
        success = await self.transmission_service.set_alt_speed(not current)

        if success:
            new_state = "enabled 🐢" if not current else "disabled 🚀"
            text = f"✅ Turtle Mode {new_state}"
        else:
            text = "❌ Failed to toggle Turtle Mode"

        enabled = config.get("transmission", {}).get("enable", False)
        new_status = await self.transmission_service.get_status()
        alt_speed = new_status.get("alt_speed_enabled", False)

        keyboard = get_transmission_settings_keyboard(enabled, alt_speed)
        await query.message.edit_text(text, reply_markup=keyboard)
        return States.SETTINGS_DOWNLOADS

    async def handle_sabnzbd_settings(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show SABnzbd settings keyboard"""
        query = update.callback_query
        await query.answer()

        enabled = config.get("sabnzbd", {}).get("enable", False)
        keyboard = get_sabnzbd_settings_keyboard(enabled)
        await query.message.edit_text(
            "📥 SABnzbd Settings", reply_markup=keyboard
        )
        return States.SETTINGS_DOWNLOADS

    async def handle_sabnzbd_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Toggle sabnzbd.enable in config"""
        query = update.callback_query
        await query.answer()

        current = config.get("sabnzbd", {}).get("enable", False)
        new_value = not current
        config.update_nested("sabnzbd.enable", new_value)
        config.save()

        status = "enabled" if new_value else "disabled"
        keyboard = get_sabnzbd_settings_keyboard(new_value)
        await query.message.edit_text(
            f"✅ SABnzbd {status}", reply_markup=keyboard,
        )
        return States.SETTINGS_DOWNLOADS

    async def handle_sabnzbd_speed(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show speed limit options or apply selected speed"""
        query = update.callback_query
        await query.answer()

        if query.data == "dl_sab_speed":
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton(
                        "25%", callback_data="dl_sab_speed_25"
                    ),
                    InlineKeyboardButton(
                        "50%", callback_data="dl_sab_speed_50"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "100%", callback_data="dl_sab_speed_100"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        f"◀️ {self.translation.get_text('Back')}",
                        callback_data="dl_back"
                    ),
                ],
            ]
            await query.message.edit_text(
                "⚡ Select speed limit:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            speed = int(query.data.replace("dl_sab_speed_", ""))
            if self.sabnzbd_service:
                await self.sabnzbd_service.set_speed_limit(speed)
            enabled = config.get("sabnzbd", {}).get("enable", False)
            keyboard = get_sabnzbd_settings_keyboard(enabled)
            await query.message.edit_text(
                f"✅ Speed limit set to {speed}%",
                reply_markup=keyboard,
            )
        return States.SETTINGS_DOWNLOADS

    async def handle_sabnzbd_pause_resume(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Pause or resume SABnzbd queue"""
        query = update.callback_query
        await query.answer()

        if query.data == "dl_sab_pause" and self.sabnzbd_service:
            await self.sabnzbd_service.pause_queue()
            text = "⏸ Queue paused"
        elif query.data == "dl_sab_resume" and self.sabnzbd_service:
            await self.sabnzbd_service.resume_queue()
            text = "▶️ Queue resumed"
        else:
            text = "❌ SABnzbd not available"

        enabled = config.get("sabnzbd", {}).get("enable", False)
        keyboard = get_sabnzbd_settings_keyboard(enabled)
        await query.message.edit_text(text, reply_markup=keyboard)
        return States.SETTINGS_DOWNLOADS

    # -- Users flow --

    async def handle_users_menu(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
        """Show users sub-menu keyboard"""
        query = update.callback_query
        await query.answer()

        security = config.get("security", {})
        admin_enabled = security.get("enableAdmin", False)
        allowlist_enabled = security.get("enableAllowlist", False)
        admin_count = len(config.get("admins", []))
        auth_count = len(config.get("authenticated_users", []))

        keyboard = get_users_keyboard(
            admin_enabled, allowlist_enabled, admin_count, auth_count
        )
        await query.message.edit_text(
            "👥 Users", reply_markup=keyboard
        )
        return States.SETTINGS_USERS

    async def handle_users_toggle(self, update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
        """Toggle a security flag (admin or allowlist)"""
        query = update.callback_query
        await query.answer()

        flag = query.data.replace("usr_toggle_", "")
        key_map = {
            "admin": "security.enableAdmin",
            "allowlist": "security.enableAllowlist",
        }
        dotted_key = key_map.get(flag)
        if not dotted_key:
            return States.SETTINGS_USERS

        security = config.get("security", {})
        field = dotted_key.split(".")[-1]
        current = security.get(field, False)
        new_value = not current

        config.update_nested(dotted_key, new_value)
        config.save()

        status = "enabled" if new_value else "disabled"
        await query.message.edit_text(
            f"✅ {flag.title()} {status}",
            reply_markup=get_users_keyboard(
                config.get("security", {}).get("enableAdmin", False),
                config.get("security", {}).get("enableAllowlist", False),
                len(config.get("admins", [])),
                len(config.get("authenticated_users", [])),
            ),
        )
        return States.SETTINGS_USERS

    # -- Misc --

    async def handle_back(self, update: Update,
                          context: ContextTypes.DEFAULT_TYPE):
        """Handle back button from settings menu → end conversation"""
        query = update.callback_query
        await query.answer()
        await query.message.edit_text(
            self.translation.get_text("End", default="Done.")
        )
        return ConversationHandler.END

    async def handle_cancel(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
        """Cancel settings conversation"""
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text(
                self.translation.get_text("End", default="Done.")
            )
        elif update.message:
            await update.message.reply_text(
                self.translation.get_text("End", default="Done.")
            )
        return ConversationHandler.END
