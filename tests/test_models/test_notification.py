"""
Tests for src.models.notification dataclasses and enums.
"""

from src.models.notification import Notification, NotificationType
from telegram.constants import ParseMode


# ---------------------------------------------------------------------------
# NotificationType enum
# ---------------------------------------------------------------------------


class TestNotificationType:
    """Tests for the NotificationType enum."""

    def test_info_exists(self):
        assert NotificationType.INFO is not None

    def test_success_exists(self):
        assert NotificationType.SUCCESS is not None

    def test_warning_exists(self):
        assert NotificationType.WARNING is not None

    def test_error_exists(self):
        assert NotificationType.ERROR is not None

    def test_admin_exists(self):
        assert NotificationType.ADMIN is not None

    def test_enum_has_exactly_five_members(self):
        assert len(NotificationType) == 5

    def test_info_value(self):
        assert NotificationType.INFO.value == "INFO"

    def test_success_value(self):
        assert NotificationType.SUCCESS.value == "SUCCESS"

    def test_warning_value(self):
        assert NotificationType.WARNING.value == "WARNING"

    def test_error_value(self):
        assert NotificationType.ERROR.value == "ERROR"

    def test_admin_value(self):
        assert NotificationType.ADMIN.value == "ADMIN"

    def test_values_match_names(self):
        for member in NotificationType:
            assert member.value == member.name


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------


class TestNotification:
    """Tests for the Notification dataclass."""

    def test_creation_all_fields(self):
        notification = Notification(
            type=NotificationType.SUCCESS,
            message="Media added successfully.",
            target_chat_ids=[12345, 67890],
            notify_admin=False,
            parse_mode=ParseMode.MARKDOWN,
        )
        assert notification.type == NotificationType.SUCCESS
        assert notification.message == "Media added successfully."
        assert notification.target_chat_ids == [12345, 67890]
        assert notification.notify_admin is False
        assert notification.parse_mode == ParseMode.MARKDOWN

    def test_default_notify_admin(self):
        notification = Notification(
            type=NotificationType.INFO,
            message="Info message.",
            target_chat_ids=[111],
        )
        assert notification.notify_admin is True

    def test_default_parse_mode(self):
        notification = Notification(
            type=NotificationType.WARNING,
            message="Warning message.",
            target_chat_ids=[222],
        )
        assert notification.parse_mode == ParseMode.HTML

    def test_all_defaults(self):
        notification = Notification(
            type=NotificationType.ERROR,
            message="Something went wrong.",
            target_chat_ids=[333],
        )
        assert notification.notify_admin is True
        assert notification.parse_mode == ParseMode.HTML

    def test_field_types(self):
        notification = Notification(
            type=NotificationType.ADMIN,
            message="Admin notification.",
            target_chat_ids=[1, 2, 3],
            notify_admin=True,
            parse_mode=ParseMode.HTML,
        )
        assert isinstance(notification.type, NotificationType)
        assert isinstance(notification.message, str)
        assert isinstance(notification.target_chat_ids, list)
        assert isinstance(notification.notify_admin, bool)
        assert isinstance(notification.parse_mode, str)

    def test_empty_target_chat_ids(self):
        notification = Notification(
            type=NotificationType.INFO,
            message="No targets.",
            target_chat_ids=[],
        )
        assert notification.target_chat_ids == []

    def test_each_notification_type(self):
        """Verify a Notification can be created with every NotificationType."""
        for ntype in NotificationType:
            notification = Notification(
                type=ntype,
                message=f"Test {ntype.name}",
                target_chat_ids=[1],
            )
            assert notification.type == ntype

    def test_parse_mode_none(self):
        notification = Notification(
            type=NotificationType.INFO,
            message="Plain text.",
            target_chat_ids=[1],
            parse_mode=None,
        )
        assert notification.parse_mode is None
